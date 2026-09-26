"""
定时任务 —— A 端按计划对 B 端下发指令（例如每天上午自动体检）。

设计取向：
  1. 不引入 APScheduler 之类的依赖：一个后台线程每 30 秒检查一次即可；
  2. 到点只触发一次（按日期记录 lastRun），避免同一天重复下发；
  3. 只对**在线**设备下发（离线设备不堆积指令，恢复后由手动操作处理）；
  4. 可按分组指定范围（例如只让某个班级每天体检）。
"""
from __future__ import annotations

import threading
import time
from typing import Any

from ..core.config import config

_CHECK_INTERVAL = 30.0

DEFAULT_PLAN: dict[str, Any] = {
    "enabled": False,
    "time": "08:00",
    "action": "checkup",
    "groups": [],
    "payload": {},
    "lastRun": "",
}


def plan() -> dict[str, Any]:
    """当前定时计划（缺项用默认值补齐）。"""
    raw = config.get("lan_schedule", {})
    merged = dict(DEFAULT_PLAN)
    if isinstance(raw, dict):
        merged.update(raw)
    return merged


class Scheduler:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="oc-lan-sched")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.wait(_CHECK_INTERVAL):
            try:
                self.tick()
            except Exception:
                continue

    def tick(self) -> bool:
        """检查一次是否到点；到点则下发。返回是否触发。"""
        current_plan = plan()
        if not current_plan.get("enabled"):
            return False

        target = str(current_plan.get("time") or "08:00").strip()
        now = time.localtime()
        if f"{now.tm_hour:02d}:{now.tm_min:02d}" != target:
            return False

        today = time.strftime("%Y-%m-%d")
        if str(current_plan.get("lastRun") or "") == today:
            return False  # 今天已执行过

        action = str(current_plan.get("action") or "checkup")
        groups = current_plan.get("groups") if isinstance(current_plan.get("groups"), list) else []
        payload = current_plan.get("payload") if isinstance(current_plan.get("payload"), dict) else {}

        from .server import server

        nodes = server.nodes()
        ids = [
            node["id"]
            for node in nodes
            if node.get("online") and (not groups or (node.get("group") or "") in groups)
        ]
        if not ids:
            return False

        result = server.send(ids, action, payload)
        server.log_event(
            "system",
            "定时任务",
            action,
            f"按计划下发到 {len(ids)} 台设备",
            True,
            str(result.get("message") or ""),
        )
        current_plan["lastRun"] = today
        config.set("lan_schedule", current_plan)
        return True


scheduler = Scheduler()
