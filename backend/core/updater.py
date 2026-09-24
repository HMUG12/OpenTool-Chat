"""
组件更新检测。

设计立场：OpenClass 把第三方软件「收编」进自己的板块后，需要知道上游何时发了
新版本，才能给用户「有新版本」的提醒。这里统一走 GitHub Releases API 查询最新
release，再与本地已集成的版本对比。

要点：
  - 网络请求带超时与内存缓存，绝不拖慢启动，也绝不因断网而抛错；
  - 查不到（断网 / 限流 / 仓库无 release）就跳过该项，不产生误报；
  - 版本号按数字序列比较，兼容 `v1.2.3`、`1.2.3`、`v2.5.0` 等常见标签写法。
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from .paths import app_root

_TIMEOUT = 6.0
_CACHE_TTL = 30 * 60  # 30 分钟内不重复请求
_HEADERS = {"User-Agent": "OpenClass", "Accept": "application/vnd.github+json"}

# 组件清单：id / 展示名 / GitHub 仓库 / 本地目录（读取 tool.json 里的 version）
# repo 留空表示该组件暂不参与在线检测（例如纯自研模块）。
COMPONENTS: list[dict[str, str]] = [
    {"id": "flclash", "name": "FlClash", "repo": "chen08209/FlClash", "dir": "flclash"},
    {"id": "hypomux", "name": "HypoMux", "repo": "Hypostasis-Cat/HypoMux", "dir": "hypomux"},
    {"id": "seelen_ui", "name": "Seelen UI", "repo": "eythaann/Seelen-UI", "dir": "seelen_ui"},
    {"id": "autowall", "name": "AutoWall", "repo": "SegoCode/AutoWall", "dir": "autowall"},
    {"id": "virus_detector", "name": "网址安全检测", "repo": "Lolitide/VirusDetector", "dir": "virus_detector"},
]

_cache: dict[str, Any] = {"at": 0.0, "items": []}
_lock = threading.Lock()


def _read_local_version(directory: str) -> str:
    """读取本地已集成的版本（tools/<dir>/tool.json 的 version 字段）。"""
    if not directory:
        return ""
    tool_json = app_root() / "tools" / directory / "tool.json"
    try:
        raw = json.loads(tool_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(raw.get("version") or "")


def _system_proxy() -> dict[str, str]:
    """读取 Windows「Internet 选项」里的系统代理。

    urllib 只认 HTTP_PROXY/HTTPS_PROXY 环境变量，不会自动跟随 Windows 代理
    设置；挂代理的机器上必须补这一层，否则所有联网查询都会超时失败。
    """
    proxies: dict[str, str] = {}
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
            server = winreg.QueryValueEx(key, "ProxyServer")[0]

        if enable and server:
            # 形态可能是 "127.0.0.1:44444"，也可能是 "http=...;https=..."
            for part in str(server).split(";"):
                part = part.strip()
                if not part:
                    continue
                scheme, addr = part.split("=", 1) if "=" in part else ("http", part)
                addr = addr if "://" in addr else f"http://{addr}"
                proxies[scheme.strip().lower()] = addr
    except (OSError, ImportError):
        pass
    return proxies


def _open(request: urllib.request.Request, timeout: float = _TIMEOUT):
    """带系统代理地发起请求（无代理时行为与 urlopen 一致）。"""
    proxies = _system_proxy()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(proxies) if proxies else None
    )
    return opener.open(request, timeout=timeout)


def _query_latest(repo: str) -> dict[str, str] | None:
    """查询仓库的最新 release；失败返回 None。"""
    if not repo:
        return None
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        with _open(urllib.request.Request(url, headers=_HEADERS)) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError):
        return None
    return {
        "latest": str(data.get("tag_name") or ""),
        "url": str(data.get("html_url") or ""),
        "publishedAt": str(data.get("published_at") or ""),
    }


def _version_tuple(value: str) -> tuple[int, ...]:
    """把版本号里的数字序列抽出来做可比较元组（v1.2.3 -> (1, 2, 3)）。"""
    return tuple(int(n) for n in re.findall(r"\d+", value or ""))


def check_updates(force: bool = False) -> list[dict[str, Any]]:
    """返回各组件的更新状态。断网时返回空列表，不抛异常。"""
    now = time.time()
    with _lock:
        if not force and _cache["items"] and (now - _cache["at"]) < _CACHE_TTL:
            return list(_cache["items"])

    items: list[dict[str, Any]] = []
    for comp in COMPONENTS:
        info = _query_latest(comp.get("repo", ""))
        if info is None or not info["latest"]:
            continue  # 查不到就不提示，避免误报

        local = _read_local_version(comp.get("dir", ""))
        items.append(
            {
                "id": comp["id"],
                "name": comp["name"],
                "current": local or "未集成",
                "latest": info["latest"],
                "hasUpdate": _version_tuple(info["latest"]) > _version_tuple(local),
                "url": info["url"],
                "publishedAt": info["publishedAt"],
            }
        )

    with _lock:
        _cache["at"] = now
        _cache["items"] = items
    return items


def updates_count() -> int:
    """有多少个组件有新版本（供角标使用，命中缓存时不发起请求）。"""
    return sum(1 for item in check_updates() if item["hasUpdate"])
