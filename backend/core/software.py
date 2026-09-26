"""
离线软件目录 —— 扫描本机安装包并一键安装。

场景：教室里没网或网不稳，电教把常用软件安装包（.exe/.msi）提前放进
软件目录，需要时装哪个点哪个，不用满盘找文件。

目录约定：<程序根目录>/software （也可在界面里指定其它目录）
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .paths import app_root

SUFFIXES = {".exe", ".msi"}
_MAX_ITEMS = 200


def default_dir() -> Path:
    return app_root() / "software"


def list_packages(directory: str = "") -> dict[str, Any]:
    """列出目录内的安装包（递归，最多 200 个）。"""
    base = Path(directory) if directory else default_dir()
    if not base.is_dir():
        return {"ok": True, "dir": str(base), "items": [], "message": "目录不存在（把安装包放进去即可）"}

    items: list[dict[str, Any]] = []
    try:
        for path in base.rglob("*"):
            if len(items) >= _MAX_ITEMS:
                break
            if path.is_file() and path.suffix.lower() in SUFFIXES:
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                items.append({"name": path.stem, "path": str(path), "size": size})
    except OSError:
        pass

    items.sort(key=lambda x: x["name"])
    return {"ok": True, "dir": str(base), "items": items, "message": ""}


def install(path: str) -> dict[str, Any]:
    """启动安装包（由系统安装向导接管，用户自行完成）。"""
    target = Path(path)
    if not target.is_file():
        return {"ok": False, "message": "安装包不存在"}
    if target.suffix.lower() not in SUFFIXES:
        return {"ok": False, "message": "只支持 .exe / .msi 安装包"}

    try:
        os.startfile(str(target))  # noqa: S606 —— 交给系统默认安装方式打开
        return {"ok": True, "message": f"已启动安装：{target.name}"}
    except OSError as exc:
        return {"ok": False, "message": f"启动失败：{exc}"}
