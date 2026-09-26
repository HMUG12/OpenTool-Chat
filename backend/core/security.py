"""
安全中心 —— 浏览防护的数据层。

与「手动输入网址检测」不同，这里承载的是**自动检测**：
  - 剪贴板网址（url_watch）
  - 浏览器访问记录（browser_watch）

每次检测（无论安全与否）都记一条事件，供前端展示「最近检测」；
白名单里的域名不再记录/告警；开关与白名单存 config，事件存
data/security_events.json（最多 200 条）。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from .config import config
from .paths import config_dir

_MAX_EVENTS = 200
_MAX_WHITELIST = 200

_lock = threading.Lock()
_events_cache: list[dict[str, Any]] | None = None


def _events_path() -> Path:
    return config_dir() / "security_events.json"


def _load() -> list[dict[str, Any]]:
    global _events_cache
    if _events_cache is not None:
        return _events_cache
    items: list[dict[str, Any]] = []
    try:
        raw = json.loads(_events_path().read_text(encoding="utf-8"))
        if isinstance(raw, list):
            items = [i for i in raw if isinstance(i, dict)][-_MAX_EVENTS:]
    except (OSError, ValueError):
        items = []
    _events_cache = items
    return items


def _save() -> None:
    try:
        _events_path().parent.mkdir(parents=True, exist_ok=True)
        _events_path().write_text(
            json.dumps(_events_cache or [], ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def _host_of(url: str) -> str:
    try:
        if "://" in url:
            return url.split("/")[2].lower()
    except IndexError:
        pass
    return url.lower()


def record(result: dict[str, Any], source: str = "clipboard") -> None:
    """记录一次自动检测结果（白名单站点跳过）。"""
    url = str(result.get("url") or "")
    if not url or is_whitelisted(url):
        return
    with _lock:
        items = _load()
        items.append(
            {
                "time": int(time.time()),
                "url": url,
                "host": _host_of(url),
                "score": int(result.get("score") or 0),
                "level": str(result.get("level") or "safe"),
                "reasons": [str(r) for r in (result.get("reasons") or [])][:4],
                "source": source,
            }
        )
        del items[:-_MAX_EVENTS]
        _save()


def events(limit: int = 120) -> list[dict[str, Any]]:
    """最近的检测事件（新的在前）。"""
    with _lock:
        items = _load()
        return list(reversed(items[-max(1, min(limit, _MAX_EVENTS)) :]))


def stats() -> dict[str, Any]:
    with _lock:
        items = list(_load())
    today = time.strftime("%Y-%m-%d")
    today_items = [
        i for i in items
        if time.strftime("%Y-%m-%d", time.localtime(float(i.get("time") or 0))) == today
    ]
    return {
        "total": len(items),
        "today": len(today_items),
        "riskTotal": len([i for i in items if i.get("level") in ("warn", "danger")]),
        "riskToday": len([i for i in today_items if i.get("level") in ("warn", "danger")]),
        "whitelistCount": len(whitelist()),
    }


def clear() -> dict[str, Any]:
    global _events_cache
    with _lock:
        _events_cache = []
        _save()
    return {"ok": True, "message": "检测记录已清空"}


# ══════════════════════════════════════════════════════════════
# 白名单
# ══════════════════════════════════════════════════════════════

def whitelist() -> list[str]:
    value = config.get("security_whitelist", [])
    return [str(v) for v in value] if isinstance(value, list) else []


def is_whitelisted(url: str) -> bool:
    host = _host_of(url)
    return any(item and item in host for item in whitelist())


def add_whitelist(domain: str) -> dict[str, Any]:
    domain = _host_of((domain or "").strip().lower())
    if not domain:
        return {"ok": False, "message": "域名不能为空"}
    items = whitelist()
    if domain not in items:
        items.append(domain)
        if not config.set("security_whitelist", items[-_MAX_WHITELIST:]):
            return {"ok": False, "message": "白名单保存失败（数据目录不可写）"}
    return {"ok": True, "message": f"已加入白名单：{domain}"}


def remove_whitelist(domain: str) -> dict[str, Any]:
    target = (domain or "").strip().lower()
    config.set("security_whitelist", [i for i in whitelist() if i != target])
    return {"ok": True, "message": "已移出白名单"}


# ══════════════════════════════════════════════════════════════
# 开关
# ══════════════════════════════════════════════════════════════

def settings() -> dict[str, Any]:
    return {
        "clipboard": bool(config.get("security_clipboard", True)),
        "browser": bool(config.get("security_browser", True)),
    }


def set_settings(clipboard: bool | None = None, browser: bool | None = None) -> dict[str, Any]:
    ok = True
    if clipboard is not None:
        ok = config.set("security_clipboard", bool(clipboard)) and ok
    if browser is not None:
        ok = config.set("security_browser", bool(browser)) and ok
    return {"ok": ok, "settings": settings()}
