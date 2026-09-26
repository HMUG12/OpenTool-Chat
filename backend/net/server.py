"""
老师机服务端 —— 内置 HTTP 服务：接收上报、下发指令、文件往返。

能力（v0.2 M2）：
  - 节点注册表：配对 + token 校验，**持久化到 SQLite**（老师机重启后
    学生机无需重新配对，仍认得彼此）；
  - 别名与分组：每台设备可改备注名、归入班级/教室分组；
  - 指令队列：每节点一队列，长轮询即时下发（秒级）；
  - **文件通道**：
      * 下发（outbox）：老师机选中的文件暂存后，学生机按 fileId 拉取；
      * 回收（inbox）：学生机把打包结果上传，按设备名归档到接收目录；
  - 掉线告警：节点由在线转为离线时自动记一条事件。

实现要点：
  - ThreadingHTTPServer：长轮询挂起不阻塞其他节点；
  - 大文件传输用分块 copy，避免整文件进内存；
  - 所有异常在单次请求内消化，服务线程不会因某台机器异常而中断。
"""
from __future__ import annotations

import shutil
import sqlite3
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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

UPLOAD_LIMIT = 1024 * 1024 * 1024  # 单次上传上限 1GB（收作业足够）
ONLINE_WINDOW = 15.0               # 超过该时间未心跳视为离线


def _db_path() -> Path:
    return config_dir() / "lan.db"


def outbox_dir() -> Path:
    path = config_dir() / "lan_outbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def inbox_dir() -> Path:
    path = config_dir() / "lan_inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Node:
    """一台已配对的学生机。"""

    def __init__(
        self,
        node_id: str,
        name: str,
        ip: str,
        info: dict[str, Any],
        alias: str = "",
        group: str = "",
        token: str = "",
        paired_at: float = 0.0,
    ) -> None:
        self.id = node_id
        self.name = name
        self.alias = alias
        self.group = group
        self.ip = ip
        self.info = info
        self.token = token or make_token()
        self.paired_at = paired_at or time.time()
        self.last_seen = time.time()
        self.pending: list[dict[str, Any]] = []
        self.results: list[dict[str, Any]] = []
        self.was_online = True

    @property
    def display_name(self) -> str:
        return self.alias or self.name

    @property
    def online(self) -> bool:
        return (time.time() - self.last_seen) < ONLINE_WINDOW

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "alias": self.alias,
            "group": self.group,
            "displayName": self.display_name,
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
        self._files: dict[str, dict[str, Any]] = {}   # fileId → 元信息
        self._lock = threading.RLock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._cond = threading.Condition(self._lock)
        self._init_db()
        self._load_nodes()

    # ── 持久化 ────────────────────────────────────────

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(_db_path()) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS events ("
                    " ts INTEGER, node_id TEXT, node_name TEXT, action TEXT,"
                    " detail TEXT, ok INTEGER, message TEXT)"
                )
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS nodes ("
                    " id TEXT PRIMARY KEY, name TEXT, alias TEXT, grp TEXT,"
                    " ip TEXT, token TEXT, paired_at REAL, info TEXT)"
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

    def _load_nodes(self) -> None:
        try:
            with sqlite3.connect(_db_path()) as conn:
                rows = conn.execute(
                    "SELECT id, name, alias, grp, ip, token, paired_at, info FROM nodes"
                ).fetchall()
        except sqlite3.Error:
            return
        import json

        for row in rows:
            try:
                info = json.loads(row[7] or "{}")
            except ValueError:
                info = {}
            node = Node(
                row[0], row[1] or row[0], row[4] or "", info,
                alias=row[2] or "", group=row[3] or "",
                token=row[5] or "", paired_at=float(row[6] or 0),
            )
            node.last_seen = 0.0        # 重启后一律先视为离线，等心跳恢复
            self._nodes[node.id] = node

    def _save_node(self, node: Node) -> None:
        import json

        try:
            with sqlite3.connect(_db_path()) as conn:
                conn.execute(
                    "INSERT INTO nodes (id, name, alias, grp, ip, token, paired_at, info)"
                    " VALUES (?,?,?,?,?,?,?,?)"
                    " ON CONFLICT(id) DO UPDATE SET name=excluded.name, alias=excluded.alias,"
                    " grp=excluded.grp, ip=excluded.ip, token=excluded.token, info=excluded.info",
                    (
                        node.id, node.name, node.alias, node.group, node.ip,
                        node.token, node.paired_at, json.dumps(node.info, ensure_ascii=False),
                    ),
                )
                conn.commit()
        except sqlite3.Error:
            pass

    def _drop_node(self, node_id: str) -> None:
        try:
            with sqlite3.connect(_db_path()) as conn:
                conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
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
        self._check_offline()
        with self._lock:
            return sorted(
                (node.snapshot() for node in self._nodes.values()),
                key=lambda item: (not item["online"], item.get("group") or "", item["displayName"]),
            )

    def _check_offline(self) -> None:
        """把"由在线转为离线"的节点记一条告警事件（每次只记一次）。"""
        with self._lock:
            for node in self._nodes.values():
                online = node.online
                if node.was_online and not online:
                    node.was_online = False
                    self._log(node.id, node.display_name, "offline", "设备已离线", False, "掉线告警")
                elif not node.was_online and online:
                    node.was_online = True
                    self._log(node.id, node.display_name, "online", "设备已恢复在线", True, "")

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
        self._drop_node(node_id)
        self._log(node_id, node.display_name, "remove", "已移出管理列表", True, "")
        return {"ok": True, "message": f"已移除 {node.display_name}"}

    def set_meta(self, node_id: str, alias: str = "", group: str = "") -> dict[str, Any]:
        """设置设备备注名与分组（空字符串表示清除）。"""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return {"ok": False, "message": "节点不存在"}
            if alias is not None:
                node.alias = alias.strip()[:40]
            if group is not None:
                node.group = group.strip()[:30]
            self._save_node(node)
            name = node.display_name
        return {"ok": True, "message": f"已更新「{name}」", "displayName": name}

    # ── 文件通道 ──────────────────────────────────────

    def stage_file(self, path: str) -> dict[str, Any]:
        """老师机把待下发文件暂存到 outbox，返回可下发的元信息。"""
        source = Path(path)
        if not source.is_file():
            return {"ok": False, "message": "文件不存在"}
        try:
            size = source.stat().st_size
        except OSError as exc:
            return {"ok": False, "message": f"读取失败：{exc}"}

        file_id = uuid.uuid4().hex[:16]
        target = outbox_dir() / f"{file_id}_{source.name}"
        try:
            shutil.copy2(source, target)
        except OSError as exc:
            return {"ok": False, "message": f"暂存失败：{exc}"}

        meta = {"id": file_id, "name": source.name, "size": size, "path": str(target)}
        with self._lock:
            self._files[file_id] = meta
            # 只保留最近 50 个待下发文件
            if len(self._files) > 50:
                for old_id in list(self._files)[:-50]:
                    old = self._files.pop(old_id, None)
                    if old:
                        try:
                            Path(old["path"]).unlink(missing_ok=True)
                        except OSError:
                            pass
        return {"ok": True, "file": {k: meta[k] for k in ("id", "name", "size")}}

    def file_meta(self, file_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._files.get(file_id)

    def save_upload(self, node: Node, name: str, data: bytes) -> dict[str, Any]:
        """保存学生机上传的文件（按设备名归档）。"""
        safe_name = Path(name or "upload.bin").name[:120]
        folder = inbox_dir() / node.display_name
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / safe_name
            target.write_bytes(data)
        except OSError as exc:
            return {"ok": False, "message": f"保存失败：{exc}"}
        return {"ok": True, "path": str(target), "size": len(data)}

    def inbox_files(self, limit: int = 200) -> list[dict[str, Any]]:
        """已收到的文件列表（老师机查看收作业结果）。"""
        items: list[dict[str, Any]] = []
        root = inbox_dir()
        try:
            for path in sorted(root.rglob("*")):
                if len(items) >= limit:
                    break
                if path.is_file():
                    try:
                        stat = path.stat()
                    except OSError:
                        continue
                    items.append(
                        {
                            "name": path.name,
                            "node": path.parent.name,
                            "size": stat.st_size,
                            "time": int(stat.st_mtime * 1000),
                            "path": str(path),
                        }
                    )
        except OSError:
            pass
        return sorted(items, key=lambda item: item["time"], reverse=True)

    # ── 指令下发 ──────────────────────────────────────

    def send(
        self,
        node_ids: list[str],
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
                self._log(node_id, node.display_name, action, str(payload)[:120], True, "指令已下发")
            self._cond.notify_all()

        if sent == 0:
            return {"ok": False, "message": "没有在线节点接收该指令"}
        return {"ok": True, "message": f"已向 {sent} 台设备下发"}

    def push_file(self, node_ids: list[str], path: str) -> dict[str, Any]:
        """暂存文件并向下发指令（学生机收到后自行拉取）。"""
        staged = self.stage_file(path)
        if not staged.get("ok"):
            return staged
        info = staged["file"]
        result = self.send(
            node_ids,
            "push_file",
            {"fileId": info["id"], "name": info["name"], "size": info["size"]},
        )
        if result.get("ok"):
            result["message"] = f"已下发文件「{info['name']}」（{info['size'] / 1048576:.1f} MB）"
        return result

    # ── HTTP 处理（由 handler 调用） ───────────────────

    def handle_pair(self, body: dict[str, Any], ip: str) -> dict[str, Any]:
        code = str(body.get("code") or "").strip()
        if code != self.pairing_code:
            return {"ok": False, "message": "配对码不正确"}
        node_info = body.get("node") if isinstance(body.get("node"), dict) else {}
        node_id = str(node_info.get("id") or make_token()[:12])
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                node = Node(node_id, str(node_info.get("name") or f"设备-{node_id[:4]}"), ip, node_info)
                self._nodes[node_id] = node
            else:
                node.last_seen = time.time()
                node.was_online = True
                node.ip = ip
                node.info = node_info
            node.ip = ip
            token = node.token
            name = node.display_name
            self._save_node(node)
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
                        node.display_name,
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
        groups = sorted({node.get("group") or "" for node in nodes if node.get("group")})
        return {
            "running": self.running,
            "port": self.port,
            "teacherName": self.teacher_name,
            "teacherId": self.teacher_id,
            "pairingCode": self.pairing_code,
            "nodeCount": len(nodes),
            "onlineCount": sum(1 for node in nodes if node["online"]),
            "offlineCount": sum(1 for node in nodes if not node["online"]),
            "groups": groups,
            "inboxDir": str(inbox_dir()),
        }


# ══════════════════════════════════════════════════════════════
# HTTP 处理器
# ══════════════════════════════════════════════════════════════

def _make_handler(server: LanServer):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "OpenClassBox-LAN/1.1"

        def log_message(self, *_args: Any) -> None:
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

        def _raw_body(self, limit: int) -> bytes | None:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            if length <= 0 or length > limit:
                return None
            remaining = length
            chunks: list[bytes] = []
            while remaining > 0:
                chunk = self.rfile.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            return b"".join(chunks)

        def _client_ip(self) -> str:
            return self.client_address[0] if self.client_address else ""

        def do_GET(self) -> None:  # noqa: N802
            from urllib.parse import parse_qs, unquote, urlparse

            parsed = urlparse(self.path)
            params = {key: value[0] for key, value in parse_qs(parsed.query).items()}

            if parsed.path == "/api/ping":
                self._reply({"ok": True, "magic": "OpenClassBox.lan", "role": "teacher",
                             "version": PROTOCOL_VERSION, "name": server.teacher_name})
                return

            if parsed.path == "/api/poll":
                try:
                    wait = float(params.get("wait", "0"))
                except ValueError:
                    wait = 0.0
                self._reply(server.handle_poll(params.get("token", ""), wait))
                return

            if parsed.path.startswith("/api/file/"):
                file_id = unquote(parsed.path[len("/api/file/"):])
                node = server._find_by_token(params.get("token", ""))
                meta = server.file_meta(file_id)
                if node is None or meta is None:
                    self._reply({"ok": False, "message": "文件不存在或令牌无效"}, 404)
                    return
                path = Path(meta["path"])
                if not path.is_file():
                    self._reply({"ok": False, "message": "文件已过期"}, 410)
                    return
                try:
                    size = path.stat().st_size
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(size))
                    self.send_header(
                        "Content-Disposition",
                        f"attachment; filename*=UTF-8''{path.name.split('_', 1)[-1]}",
                    )
                    self.end_headers()
                    with path.open("rb") as handle:
                        shutil.copyfileobj(handle, self.wfile, 1024 * 1024)
                except OSError:
                    pass
                return

            self._reply({"ok": False, "message": "未知接口"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(self.path)
            params = {key: value[0] for key, value in parse_qs(parsed.query).items()}

            if parsed.path == "/api/pair":
                self._reply(server.handle_pair(self._body(), self._client_ip()))
                return
            if parsed.path == "/api/report":
                self._reply(server.handle_report(self._body(), self._client_ip()))
                return
            if parsed.path == "/api/result":
                self._reply(server.handle_result(self._body()))
                return
            if parsed.path == "/api/upload":
                node = server._find_by_token(params.get("token", ""))
                if node is None:
                    self._reply({"ok": False, "message": "令牌无效"}, 403)
                    return
                data = self._raw_body(UPLOAD_LIMIT)
                if data is None:
                    self._reply({"ok": False, "message": "空文件或超过大小限制"}, 413)
                    return
                result = server.save_upload(node, params.get("name", "upload.bin"), data)
                if result.get("ok"):
                    server._log(
                        node.id, node.display_name, "upload",
                        f"收到 {params.get('name', '')}（{len(data) / 1048576:.1f} MB）",
                        True, "文件已回收",
                    )
                self._reply(result)
                return
            self._reply({"ok": False, "message": "未知接口"}, 404)

    return Handler


server = LanServer()
