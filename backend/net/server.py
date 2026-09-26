"""
老师机服务端 —— 内置 HTTP 服务：接收学生机上报、下发远程指令。

职责划分：
  - 节点注册表：配对、token 校验、状态快照（内存 + SQLite 持久化）
  - 指令队列：每个节点一个队列，长轮询即时下发（秒级）
  - 事件日志：谁在什么时候对哪台机器做了什么、结果如何

实现要点：
  - ThreadingHTTPServer：长轮询挂起时不会阻塞其他节点的请求；
  - 仅监听本机（局域网可访问），不主动对外暴露；
  - 任何异常都在单次请求内消化，服务线程不会因某台机器异常而中断。
"""
from __future__ import annotations

import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ..core.paths import config_dir
from .proto import (
    DEFAULT_HTTP_PORT,
    POLL_HOLD_SECONDS,
    PROTOCOL_VERSION,
    dumps,
    loads,
    make_token,
    now_ms,
    pairing_code,
)


def _db_path():
    return config_dir() / "lan.db"


class Node:
    """一台已配对的学生机。"""

    def __init__(self, node_id: str, name: str, ip: str, info: dict[str, Any]) -> None:
        self.id = node_id
        self.name = name
        self.ip = ip
        self.info = info
        self.token = make_token()
        self.paired_at = time.time()
        self.last_seen = time.time()
        self.pending: list[dict[str, Any]] = []
        self.results: list[dict[str, Any]] = []

    @property
    def online(self) -> bool:
        return (time.time() - self.last_seen) < 15

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "ip": self.ip,
            "online": self.online,
            "lastSeen": int(self.last_seen * 1000),
            "pairedAt": int(self.paired_at * 1000),
            "info": self.info,
            "pending": len(self.pending),
        }


class LanServer:
    def __init__(self, teacher_name: str = "") -> None:
        self.teacher_name = teacher_name
        self.pairing_code = pairing_code()
        self.teacher_id = make_token()[:12]
        self.port = DEFAULT_HTTP_PORT
        self._nodes: dict[str, Node] = {}
        self._events: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._cond = threading.Condition(self._lock)
        self._init_db()

    # ── 持久化 ────────────────────────────────────────

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(_db_path()) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS events ("
                    " ts INTEGER, node_id TEXT, node_name TEXT, action TEXT,"
                    " detail TEXT, ok INTEGER, message TEXT)"
                )
                conn.commit()
        except sqlite3.Error:
            pass

    def _save_event(self, event: dict[str, Any]) -> None:
        try:
            with sqlite3.connect(_db_path()) as conn:
                conn.execute(
                    "INSERT INTO events (ts, node_id, node_name, action, detail, ok, message)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (
                        event["ts"],
                        event.get("nodeId", ""),
                        event.get("nodeName", ""),
                        event.get("action", ""),
                        event.get("detail", ""),
                        1 if event.get("ok") else 0,
                        event.get("message", ""),
                    ),
                )
                conn.commit()
        except sqlite3.Error:
            pass

    # ── 生命周期 ──────────────────────────────────────

    def start(self, port: int = DEFAULT_HTTP_PORT) -> dict[str, Any]:
        if self._httpd is not None:
            return {"ok": True, "message": "服务已在运行", "port": self.port}
        self.port = int(port)

        handler = _make_handler(self)
        try:
            httpd = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
        except OSError as exc:
            return {"ok": False, "message": f"端口 {self.port} 无法监听：{exc}"}
        httpd.daemon_threads = True
        self._httpd = httpd
        self._thread = threading.Thread(target=httpd.serve_forever, daemon=True, name="oc-lan-http")
        self._thread.start()
        self._log("system", "老师机", "start", f"服务端启动，端口 {self.port}", True, "")
        return {"ok": True, "message": f"服务端已启动（端口 {self.port}）", "port": self.port}

    def stop(self) -> dict[str, Any]:
        if self._httpd is None:
            return {"ok": True, "message": "服务未运行"}
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        except OSError:
            pass
        self._httpd = None
        self._thread = None
        self._log("system", "老师机", "stop", "服务端已停止", True, "")
        return {"ok": True, "message": "服务端已停止"}

    @property
    def running(self) -> bool:
        return self._httpd is not None

    # ── 节点与事件 ────────────────────────────────────

    def nodes(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(
                (node.snapshot() for node in self._nodes.values()),
                key=lambda item: (not item["online"], item["name"]),
            )

    def events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._events[-max(1, min(limit, 500)):]))

    def _log(
        self,
        node_id: str,
        node_name: str,
        action: str,
        detail: str,
        ok: bool,
        message: str,
    ) -> None:
        event = {
            "ts": now_ms(),
            "nodeId": node_id,
            "nodeName": node_name,
            "action": action,
            "detail": detail,
            "ok": ok,
            "message": message,
        }
        with self._lock:
            self._events.append(event)
            del self._events[:-500]
        self._save_event(event)

    def reset_code(self) -> str:
        with self._lock:
            self.pairing_code = pairing_code()
            return self.pairing_code

    def remove_node(self, node_id: str) -> dict[str, Any]:
        with self._lock:
            node = self._nodes.pop(node_id, None)
        if node is None:
            return {"ok": False, "message": "节点不存在"}
        self._log(node_id, node.name, "remove", "已移出管理列表", True, "")
        return {"ok": True, "message": f"已移除 {node.name}"}

    # ── 指令下发 ──────────────────────────────────────

    def send(self, node_ids: list[str], action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        sent = 0
        with self._cond:
            for node_id in node_ids:
                node = self._nodes.get(node_id)
                if node is None or not node.online:
                    continue
                command = {
                    "seq": f"{int(time.time() * 1000)}-{len(node.pending)}",
                    "action": action,
                    "payload": payload,
                    "issuedAt": now_ms(),
                }
                node.pending.append(command)
                sent += 1
                self._log(node_id, node.name, action, str(payload)[:120], True, "指令已下发")
            self._cond.notify_all()

        if sent == 0:
            return {"ok": False, "message": "没有在线节点接收该指令"}
        return {"ok": True, "message": f"已向 {sent} 台设备下发「{action}」"}

    # ── HTTP 处理（由 handler 调用） ───────────────────

    def handle_pair(self, body: dict[str, Any], ip: str) -> dict[str, Any]:
        code = str(body.get("code") or "").strip()
        if code != self.pairing_code:
            return {"ok": False, "message": "配对码不正确"}
        node_info = body.get("node") if isinstance(body.get("node"), dict) else {}
        node_id = str(node_info.get("id") or make_token()[:12])
        name = str(node_info.get("name") or f"设备-{node_id[:4]}")
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                node = Node(node_id, name, ip, node_info)
                self._nodes[node_id] = node
            else:
                node.last_seen = time.time()
                node.info = node_info
            token = node.token
        self._log(node_id, name, "pair", f"来自 {ip}", True, "配对成功")
        return {
            "ok": True,
            "token": token,
            "teacher": self.teacher_name,
            "interval": 5,
            "version": PROTOCOL_VERSION,
        }

    def handle_report(self, body: dict[str, Any], ip: str) -> dict[str, Any]:
        token = str(body.get("token") or "")
        node = self._find_by_token(token)
        if node is None:
            return {"ok": False, "message": "令牌无效，请重新配对"}
        with self._cond:
            node.last_seen = time.time()
            node.ip = ip
            if isinstance(body.get("info"), dict):
                node.info = body["info"]
            commands = list(node.pending)
            node.pending.clear()
        return {"ok": True, "commands": commands}

    def handle_poll(self, token: str, wait: float) -> dict[str, Any]:
        node = self._find_by_token(token)
        if node is None:
            return {"ok": False, "message": "令牌无效，请重新配对"}
        deadline = time.time() + max(0.0, min(wait, POLL_HOLD_SECONDS))
        with self._cond:
            node.last_seen = time.time()
            while not node.pending and time.time() < deadline:
                self._cond.wait(timeout=max(0.2, deadline - time.time()))
            commands = list(node.pending)
            node.pending.clear()
        return {"ok": True, "commands": commands}

    def handle_result(self, body: dict[str, Any]) -> dict[str, Any]:
        token = str(body.get("token") or "")
        node = self._find_by_token(token)
        if node is None:
            return {"ok": False, "message": "令牌无效"}
        results = body.get("results")
        if isinstance(results, list):
            with self._lock:
                for item in results[:20]:
                    if not isinstance(item, dict):
                        continue
                    node.results.append(item)
                    del node.results[:-50]
                    self._log(
                        node.id,
                        node.name,
                        str(item.get("action") or ""),
                        str(item.get("detail") or "")[:160],
                        bool(item.get("ok")),
                        str(item.get("message") or "")[:200],
                    )
        return {"ok": True}

    def _find_by_token(self, token: str) -> Node | None:
        if not token:
            return None
        with self._lock:
            for node in self._nodes.values():
                if node.token == token:
                    return node
        return None

    def status(self) -> dict[str, Any]:
        nodes = self.nodes()
        return {
            "running": self.running,
            "port": self.port,
            "teacherName": self.teacher_name,
            "teacherId": self.teacher_id,
            "pairingCode": self.pairing_code,
            "nodeCount": len(nodes),
            "onlineCount": sum(1 for node in nodes if node["online"]),
        }


# ══════════════════════════════════════════════════════════════
# HTTP 处理器
# ══════════════════════════════════════════════════════════════

def _make_handler(server: LanServer):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "OpenClassBox-LAN/1.0"

        def log_message(self, *_args: Any) -> None:  # 静默，不污染控制台
            return

        def _reply(self, payload: dict[str, Any], code: int = 200) -> None:
            body = dumps(payload)
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def _body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return {}
            if length <= 0 or length > 8 * 1024 * 1024:
                return {}
            try:
                return loads(self.rfile.read(length))
            except OSError:
                return {}

        def _client_ip(self) -> str:
            return self.client_address[0] if self.client_address else ""

        def do_GET(self) -> None:  # noqa: N802
            path, _, query = self.path.partition("?")
            params = dict(
                item.split("=", 1) for item in query.split("&") if "=" in item
            ) if query else {}

            if path == "/api/ping":
                self._reply({"ok": True, "magic": "OpenClassBox.lan", "role": "teacher",
                             "version": PROTOCOL_VERSION, "name": server.teacher_name})
                return
            if path == "/api/poll":
                wait = 0.0
                try:
                    wait = float(params.get("wait", "0"))
                except ValueError:
                    wait = 0.0
                self._reply(server.handle_poll(params.get("token", ""), wait))
                return
            self._reply({"ok": False, "message": "未知接口"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.partition("?")[0]
            body = self._body()
            if path == "/api/pair":
                self._reply(server.handle_pair(body, self._client_ip()))
                return
            if path == "/api/report":
                self._reply(server.handle_report(body, self._client_ip()))
                return
            if path == "/api/result":
                self._reply(server.handle_result(body))
                return
            self._reply({"ok": False, "message": "未知接口"}, 404)

    return Handler


server = LanServer()
