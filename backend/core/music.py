"""
内置音乐 —— 本地音乐库扫描 / 搜索 / 播放支持。

播放交给前端 <audio> 标签，因此这里起一个只监听 127.0.0.1 的轻量 HTTP 服务，
把本地音频以流的形式提供给前端。只服务"音乐目录内"的文件，避免任意文件读取。

在线搜索接口预留（音源可插拔），当前先落地本地库搜索。
"""
from __future__ import annotations

import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

AUDIO_SUFFIXES = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac", ".opus"}

_MIME = {
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".aac": "audio/aac",
    ".opus": "audio/opus",
}

_server: ThreadingHTTPServer | None = None
_port = 0
_allowed: list[Path] = []
_lock = threading.Lock()


def library_dirs() -> list[Path]:
    """默认扫描的音乐目录。

    注意：不要扫 Downloads —— 那里常堆积海量文件，递归会把搜索卡死。
    """
    home = Path(os.path.expanduser("~"))
    return [home / "Music"]


def _is_allowed(path: Path) -> bool:
    for base in _allowed:
        try:
            path.resolve().relative_to(base.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


# 扫描结果缓存（同一批目录不重复递归）+ 文件数上限，避免大目录把界面卡住
_cache: dict[str, Any] = {"key": (), "items": []}
_MAX_SCAN_FILES = 8000


def scan_library(extra_dirs: list[str] | None = None, force: bool = False) -> list[dict[str, Any]]:
    """扫描音乐目录，返回音频文件列表（带缓存与文件数上限）。"""
    global _allowed
    targets = [Path(d) for d in extra_dirs] if extra_dirs else library_dirs()
    _allowed = [t for t in targets if t.exists()]

    key = tuple(str(t) for t in _allowed)
    if not force and _cache["key"] == key and _cache["items"]:
        return list(_cache["items"])

    items: list[dict[str, Any]] = []
    scanned = 0
    for base in _allowed:
        try:
            for p in base.rglob("*"):
                scanned += 1
                if scanned > _MAX_SCAN_FILES:
                    break
                if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES:
                    try:
                        size = p.stat().st_size
                    except OSError:
                        continue
                    items.append({"name": p.stem, "path": str(p), "size": size})
        except OSError:
            continue

    _cache.update({"key": key, "items": items})
    return items


def search(keyword: str = "", extra_dirs: list[str] | None = None) -> list[dict[str, Any]]:
    """按关键词过滤本地音乐；空关键词返回全部（最多 200 条）。"""
    items = scan_library(extra_dirs)
    kw = (keyword or "").strip().lower()
    if not kw:
        return items[:200]
    return [i for i in items if kw in i["name"].lower()][:200]


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/file":
            self.send_error(404)
            return

        query = urllib.parse.parse_qs(parsed.query)
        raw = (query.get("path") or [""])[0]
        target = Path(raw)
        if not raw or not _is_allowed(target) or not target.is_file():
            self.send_error(403)
            return

        try:
            data = target.read_bytes()
        except OSError:
            self.send_error(500)
            return

        self.send_response(200)
        self.send_header("Content-Type", _MIME.get(target.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: Any) -> None:
        """静默：不在控制台刷访问日志。"""


def start_media_server() -> int:
    """启动本地媒体服务（仅 127.0.0.1，端口随机），返回端口。"""
    global _server, _port
    with _lock:
        if _server:
            return _port
        _server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        _port = _server.server_address[1]
        threading.Thread(target=_server.serve_forever, daemon=True).start()
        return _port


def media_url(path: str) -> str:
    """把本地音频路径转成前端可直接播放的 URL。"""
    port = start_media_server()
    return f"http://127.0.0.1:{port}/file?path={urllib.parse.quote(str(path))}"


# ── 在线音源（可插拔） ────────────────────────────────────────
# 实测：网易云搜索接口可用；B 站返回 412（反爬需签名）、QQ 老接口返回 500。
# 因此先落地网易云，B 站 / QQ 的接口就绪后按同样结构接入即可。

_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

PLATFORMS = {"netease", "bilibili", "qq"}


def _request(url: str, headers: dict[str, str] | None = None) -> bytes:
    """带系统代理地请求，失败抛出。"""
    import urllib.request

    from .updater import _system_proxy

    proxies = _system_proxy()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(proxies) if proxies else None
    )
    req = urllib.request.Request(url, headers={**_UA, **(headers or {})})
    with opener.open(req, timeout=10) as resp:
        return resp.read()


def search_online(keyword: str, platform: str = "netease", limit: int = 20) -> list[dict[str, Any]]:
    """在线搜索音频。返回统一结构：id / name / artist / platform。"""
    import json

    kw = urllib.parse.quote((keyword or "").strip())
    if not kw:
        return []

    if platform == "netease":
        raw = _request(
            f"http://music.163.com/api/search/get?s={kw}&type=1&limit={limit}",
            {"Referer": "http://music.163.com/"},
        )
        songs = (json.loads(raw).get("result") or {}).get("songs") or []
        return [
            {
                "id": str(s.get("id") or ""),
                "name": s.get("name") or "",
                "artist": ", ".join(a.get("name", "") for a in (s.get("artists") or [])),
                "platform": "netease",
            }
            for s in songs
            if s.get("id")
        ]

    # bilibili / qq 当前接口不可用（412 / 500），返回空而不是报错
    return []


def fetch_online(song_id: str, platform: str = "netease") -> str:
    """把在线音频拉取到本地缓存目录，返回本地路径（失败返回空串）。"""
    if platform != "netease" or not song_id:
        return ""

    cache_dir = Path(os.path.expanduser("~")) / "Music" / "OpenClass-Box"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"netease_{song_id}.mp3"
    if dest.is_file():
        return str(dest)

    data = _request(
        f"http://music.163.com/song/media/outer/url?id={song_id}.mp3",
        {"Referer": "http://music.163.com/"},
    )
    if not data:
        return ""
    dest.write_bytes(data)
    return str(dest)
