"""
桌面壁纸 —— OpenClass-Box 自研实现（非外置程序）。

支持三类壁纸：
  1. 静态图片（jpg/png/bmp/webp）——走 Windows 原生接口，可调位置与大小；
  2. 动图（gif）与视频（mp4/webm/mkv/avi）——用 mpv 渲染到桌面 WorkerW 图层；
  3. 直接导入——把任意位置的壁纸文件复制进程序数据目录统一管理。

"位置 / 大小"两级控制：
  - 样式（填充 / 适应 / 拉伸 / 平铺 / 居中 / 跨屏）→ 写注册表 WallpaperStyle；
  - 自定义尺寸（屏幕百分比）→ 用 Pillow 缩放并居中合成后再设为拉伸。

动态壁纸依赖 mpv（开源播放器）：把 mpv.exe 放到 tools/mpv/ 即可启用；
没有 mpv 时会明确告知，不会静默失败。
"""
from __future__ import annotations

import ctypes
import os
import random
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from .paths import app_root, config_dir

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
GIF_SUFFIXES = {".gif"}
VIDEO_SUFFIXES = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv"}
ALL_SUFFIXES = IMAGE_SUFFIXES | GIF_SUFFIXES | VIDEO_SUFFIXES

SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

_MAX_LIST = 400

# 样式 → (WallpaperStyle, TileWallpaper)
_STYLES: dict[str, tuple[str, str]] = {
    "fill": ("10", "0"),     # 填充（等比裁剪）
    "fit": ("6", "0"),       # 适应（留黑边）
    "stretch": ("2", "0"),   # 拉伸
    "tile": ("0", "1"),      # 平铺
    "center": ("0", "0"),    # 居中
    "span": ("22", "0"),     # 跨屏
}

_dynamic_lock = threading.Lock()
_dynamic_proc: "subprocess.Popen[bytes] | None" = None
_dynamic_path = ""


def _wallpaper_dir() -> Path:
    """导入壁纸的存放目录（跟随程序目录，便携）。"""
    return config_dir() / "wallpapers"


def default_dir() -> Path:
    """默认扫描目录：用户「图片」文件夹。"""
    return Path(os.path.expanduser("~")) / "Pictures"


def _kind_of(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in GIF_SUFFIXES:
        return "gif"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return ""


def list_wallpapers(directory: str = "") -> dict[str, Any]:
    """列出可用壁纸：程序导入目录（不递归）+ 指定目录/图片文件夹（递归）。

    返回 {items: [{name, path, kind}], importedDir}
    kind: image / gif / video
    """
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        if len(items) >= _MAX_LIST or not path.is_file():
            return
        kind = _kind_of(path)
        if not kind:
            return
        key = str(path).lower()
        if key in seen:
            return
        seen.add(key)
        items.append({"name": path.stem, "path": str(path), "kind": kind})

    import_dir = _wallpaper_dir()
    if import_dir.is_dir():
        try:
            for path in sorted(import_dir.iterdir()):
                _add(path)
        except OSError:
            pass

    scan_dir = Path(directory) if directory else default_dir()
    if scan_dir.is_dir():
        try:
            for path in scan_dir.rglob("*"):
                _add(path)
                if len(items) >= _MAX_LIST:
                    break
        except OSError:
            pass

    images = [i for i in items if i["kind"] == "image"]
    dynamic = [i for i in items if i["kind"] in ("gif", "video")]
    return {"items": images + dynamic, "importedDir": str(_wallpaper_dir())}


def import_file(source: str) -> dict[str, Any]:
    """把外部壁纸文件复制进程序数据目录（重名自动加序号）。"""
    src = Path(source)
    if not src.is_file():
        return {"ok": False, "path": "", "message": "文件不存在"}
    suffix = src.suffix.lower()
    if suffix not in ALL_SUFFIXES:
        return {"ok": False, "path": "", "message": f"不支持的格式：{suffix or '未知'}"}

    target_dir = _wallpaper_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / src.name
        index = 1
        while target.exists() and target.resolve() != src.resolve():
            target = target_dir / f"{src.stem}_{index}{suffix}"
            index += 1
        if target.resolve() != src.resolve():
            shutil.copy2(src, target)
    except OSError as exc:
        return {"ok": False, "path": "", "message": f"导入失败：{exc}"}
    return {"ok": True, "path": str(target), "message": f"已导入 {target.name}"}


def _screen_size() -> tuple[int, int]:
    try:
        user32 = ctypes.windll.user32
        return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    except (AttributeError, OSError):
        return 1920, 1080


def _apply_style(style: str) -> None:
    """把位置/大小样式写进注册表（Windows 桌面据此渲染）。"""
    wallpaper_style, tile = _STYLES.get(style, _STYLES["fill"])
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, wallpaper_style)
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, tile)
    except (OSError, ImportError):
        pass


def _scaled_variant(src: Path, scale: int) -> Path | None:
    """按屏幕尺寸的百分比缩放并居中合成（用于「自定义大小」）。"""
    try:
        from PIL import Image
    except ImportError:
        return None

    screen_w, screen_h = _screen_size()
    target_w = max(1, int(screen_w * scale / 100))
    target_h = max(1, int(screen_h * scale / 100))
    out_dir = _wallpaper_dir()
    out = out_dir / f".scaled_{src.stem}_{scale}.jpg"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as img:
            rgb = img.convert("RGB")
            resized = rgb.resize((target_w, target_h), Image.LANCZOS)
            canvas = Image.new("RGB", (screen_w, screen_h), (0, 0, 0))
            canvas.paste(resized, ((screen_w - target_w) // 2, (screen_h - target_h) // 2))
            canvas.save(out, "JPEG", quality=92)
    except (OSError, ValueError):
        return None
    return out


def set_wallpaper(path: str, style: str = "fill", scale: int = 100) -> dict[str, Any]:
    """设置静态图片壁纸。

    style: fill / fit / stretch / tile / center / span
    scale: 屏幕百分比（100 = 原图；其它值用 Pillow 预缩放后居中）
    """
    target = Path(path)
    if not target.is_file():
        return {"ok": False, "path": "", "message": "图片不存在"}

    _apply_style(style)
    use = target
    if scale != 100:
        scaled = _scaled_variant(target, scale)
        if scaled is not None:
            use = scaled
            _apply_style("stretch")  # 预缩放图按拉伸铺满 = 自定义大小 + 居中

    try:
        ok = bool(
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                str(use),
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
            )
        )
    except (AttributeError, OSError):
        return {"ok": False, "path": str(target), "message": "设置失败（系统接口不可用）"}

    return {"ok": ok, "path": str(target), "message": "壁纸已更换" if ok else "设置失败"}


def current_wallpaper() -> str:
    """读取当前桌面壁纸路径。"""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
            return str(winreg.QueryValueEx(key, "WallPaper")[0])
    except (OSError, ImportError):
        return ""


# ══════════════════════════════════════════════════════════════
# 动态壁纸（GIF / 视频）：mpv 渲染到桌面 WorkerW 层
# ══════════════════════════════════════════════════════════════

def _find_mpv() -> Path | None:
    """定位 mpv 播放器：tools/mpv/ → PATH。"""
    candidates = [
        app_root() / "tools" / "mpv" / "mpv.exe",
        app_root() / "tools" / "mpv" / "mpv-x86_64" / "mpv.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    found = shutil.which("mpv")
    return Path(found) if found else None


def _find_workerw() -> int:
    """定位桌面壁纸层窗口（WorkerW），供 mpv 嵌入渲染。"""
    try:
        user32 = ctypes.windll.user32
    except (AttributeError, OSError):
        return 0

    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return 0

    # 0x052C：让 Progman 分裂出 WorkerW 的内部消息
    result = ctypes.c_ulong()
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(result))

    defview = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
    if defview:
        worker = user32.FindWindowExW(0, defview, "WorkerW", None)
        if worker:
            return int(worker)

    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum(hwnd, _lparam):  # type: ignore[no-untyped-def]
        if user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None):
            worker = user32.FindWindowExW(0, hwnd, "WorkerW", None)
            if worker:
                found.append(int(worker))
                return False
        return True

    user32.EnumWindows(_enum, 0)
    return found[0] if found else 0


def dynamic_status() -> dict[str, Any]:
    with _dynamic_lock:
        proc = _dynamic_proc
        path = _dynamic_path
    running = bool(proc is not None and proc.poll() is None)
    return {"running": running, "path": path if running else "", "hasMpv": _find_mpv() is not None}


def stop_dynamic() -> dict[str, Any]:
    """停止视频/动图壁纸。"""
    global _dynamic_proc, _dynamic_path
    with _dynamic_lock:
        proc = _dynamic_proc
        _dynamic_proc = None
        _dynamic_path = ""
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except (OSError, subprocess.SubprocessError):
            try:
                proc.kill()
            except OSError:
                pass
    return {"ok": True, "message": "已停止动态壁纸"}


def set_dynamic(path: str, muted: bool = True) -> dict[str, Any]:
    """设置 GIF / 视频壁纸（mpv 渲染进桌面壁纸层）。"""
    global _dynamic_proc, _dynamic_path

    target = Path(path)
    if not target.is_file():
        return {"ok": False, "message": "文件不存在"}
    if _kind_of(target) not in ("gif", "video"):
        return {"ok": False, "message": "仅动图与视频支持动态壁纸"}

    mpv = _find_mpv()
    if mpv is None:
        return {
            "ok": False,
            "message": "未找到 mpv 播放器：把 mpv.exe 放到 tools/mpv/ 后重试（动态壁纸用它渲染）",
        }

    worker = _find_workerw()
    if not worker:
        return {"ok": False, "message": "未能定位桌面壁纸层（WorkerW），当前系统可能不支持"}

    stop_dynamic()

    args = [
        str(mpv),
        f"--wid={worker}",
        "--loop-file=inf",
        "--no-osc",
        "--no-input-default-bindings",
        "--no-border",
        "--keep-open=no",
        "--really-quiet",
    ]
    if muted:
        args.append("--no-audio")
    args.append(str(target))

    try:
        proc = subprocess.Popen(
            args,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return {"ok": False, "message": f"启动 mpv 失败：{exc}"}

    with _dynamic_lock:
        _dynamic_proc = proc
        _dynamic_path = str(target)

    return {"ok": True, "message": "动态壁纸已启动", "path": str(target)}


def random_wallpaper(directory: str = "") -> dict[str, Any]:
    """从目录随机换一张静态壁纸。"""
    data = list_wallpapers(directory)
    images = [i for i in data["items"] if i["kind"] == "image"]
    if not images:
        return {"ok": False, "message": "没有可用图片"}
    pick = random.choice(images)
    result = set_wallpaper(pick["path"])
    return {**result, "name": pick["name"]}
