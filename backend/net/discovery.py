"""
局域网自动发现 —— 学生机不必手填 IP 就能找到老师机。

两种用法：
  - broadcast_search()      学生机：广播探测，收集 3 秒内的老师机应答；
  - DiscoveryResponder      老师机：常驻监听探测包并应答自身信息。

容错原则：所有网络异常一律静默，找不到老师机时学生机只是"未连接"，
绝不影响单机功能使用。
"""
from __future__ import annotations

import socket
import threading
import time
from typing import Any

from .proto import DISCOVERY_PORT, MAGIC, PROTOCOL_VERSION, dumps, loads


def broadcast_search(timeout: float = 3.0) -> list[dict[str, Any]]:
    """学生机：广播搜索老师机，返回候选列表（按 IP 去重）。"""
    found: dict[str, dict[str, Any]] = {}
    payload = dumps(
        {"magic": MAGIC, "v": PROTOCOL_VERSION, "role": "student", "action": "who_is_teacher"}
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.5)
        for target in ("255.255.255.255", "<broadcast>"):
            try:
                sock.sendto(payload, (target, DISCOVERY_PORT))
            except OSError:
                continue

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                raw, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            data = loads(raw)
            if data.get("magic") != MAGIC or data.get("role") != "teacher":
                continue
            data["ip"] = addr[0]
            found[addr[0]] = data
    finally:
        sock.close()
    return list(found.values())


class DiscoveryResponder:
    """老师机：监听探测包，应答自身（名称 / HTTP 端口 / 是否需要配对码）。"""

    def __init__(self, http_port: int, name: str, teacher_id: str) -> None:
        self._http_port = http_port
        self._name = name
        self._teacher_id = teacher_id
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="oc-lan-discovery")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _loop(self) -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", DISCOVERY_PORT))
            sock.settimeout(1.0)
            self._sock = sock
        except OSError:
            return  # 端口被占用：不阻断主流程

        reply = dumps(
            {
                "magic": MAGIC,
                "v": PROTOCOL_VERSION,
                "role": "teacher",
                "name": self._name,
                "teacherId": self._teacher_id,
                "httpPort": self._http_port,
            }
        )
        while not self._stop.is_set():
            try:
                raw, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            data = loads(raw)
            if data.get("magic") == MAGIC and data.get("action") == "who_is_teacher":
                try:
                    sock.sendto(reply, addr)
                except OSError:
                    continue
        try:
            sock.close()
        except OSError:
            pass
