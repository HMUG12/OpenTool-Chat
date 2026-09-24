"""
桌面壁纸 —— OpenClass-Box 自研实现（非外置程序）。

直接用 Windows API（SystemParametersInfoW）设置桌面壁纸，并支持从指定目录
随机更换，作为「自动壁纸」的轻量实现。全部逻辑在本应用内，无外部依赖。
"""
from __future__ import annotations

import ctypes
import os
import random
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

_MAX_LIST = 300


def default_dir() -> Path:
    """默认壁纸目录：用户「图片」文件夹。"""
    return Path(os.path.expanduser("~")) / "Pictures"


def list_images(directory: str = "") -> list[dict[str, Any]]:
    """列出目录内可用作壁纸的图片（最多 300 张）。"""
    base = Path(directory) if directory else default_dir()
    if not base.is_dir():
        return []

    items: list[dict[str, Any]] = []
    try:
        for p in base.rglob("*"):
            if len(items) >= _MAX_LIST:
                break
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES:
                items.append({"name": p.stem, "path": str(p)})
    except OSError:
        pass
    return items


def set_wallpaper(path: str) -> bool:
    """把指定图片设为桌面壁纸。"""
    target = Path(path)
    if not target.is_file():
        return False
    try:
        return bool(
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                str(target),
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
            )
        )
    except (AttributeError, OSError):
        return False


def random_wallpaper(directory: str = "") -> dict[str, Any]:
    """从目录随机换一张壁纸。"""
    items = list_images(directory)
    if not items:
        return {"ok": False, "message": "目录中没有可用图片"}
    pick = random.choice(items)
    ok = set_wallpaper(pick["path"])
    return {
        "ok": ok,
        "path": pick["path"],
        "name": pick["name"],
        "message": "已更换壁纸" if ok else "设置失败",
    }
