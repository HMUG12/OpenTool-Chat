"""
浏览器访问自动检测 —— 用户浏览网站时自动发现风险，无需手动输入/复制。

做法：读取 Chrome / Edge 的历史库（SQLite），取其最新一条访问记录，
发现新访问的网址就交给 url_guard 评分，风险则投递告警供前端提示。

要点：
  - 历史库被浏览器独占，必须先复制副本再只读打开，绝不碰原文件；
  - 只做提示，不干预浏览；
  - 全程异常静默，浏览器未安装或库结构变化都不影响应用运行。
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from .url_guard import check_url
from .url_watch import push_alert

_INTERVAL = 3.0
_MAX_ALERTS_PER_TICK = 3

# Chrome / Edge 的用户数据目录（含多 Profile：Default、Profile 1 …）
_BROWSER_ROOTS = [
    ("Chrome", Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"),
    ("Edge", Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"),
]


def _history_files() -> list[Path]:
    found: list[Path] = []
    for _, root in _BROWSER_ROOTS:
        if not root.is_dir():
            continue
        try:
            for db in root.glob("*/History"):
                if db.is_file():
                    found.append(db)
        except OSError:
            continue
    return found


def _latest_visit(history: Path) -> tuple[str, int] | None:
    """复制历史库后只读查询最新访问记录，返回 (url, last_visit_time)。"""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "History"
            shutil.copy2(history, copy)
            con = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
            try:
                row = con.execute(
                    "SELECT url, last_visit_time FROM urls "
                    "ORDER BY last_visit_time DESC LIMIT 1"
                ).fetchone()
            finally:
                con.close()
        if row and row[0]:
            return str(row[0]), int(row[1] or 0)
    except (OSError, sqlite3.Error, ValueError):
        return None
    return None


def _loop() -> None:
    seen: dict[str, int] = {}
    while True:
        try:
            checked = 0
            for history in _history_files():
                got = _latest_visit(history)
                if not got:
                    continue
                url, stamp = got
                key = str(history)
                if seen.get(key) == stamp:
                    continue  # 该库没有新的访问
                seen[key] = stamp
                if checked >= _MAX_ALERTS_PER_TICK:
                    continue
                checked += 1
                if url.startswith(("http://", "https://")):
                    result: dict[str, Any] = check_url(url)
                    if result["level"] != "safe":
                        push_alert(result)
        except Exception:
            pass
        time.sleep(_INTERVAL)


_started = False
_lock = threading.Lock()


def start() -> None:
    """启动浏览器访问监听（幂等）。"""
    global _started
    with _lock:
        if _started:
            return
        _started = True
    threading.Thread(target=_loop, daemon=True, name="oc-browser-watch").start()
