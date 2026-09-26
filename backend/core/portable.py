"""
便携与急救模式 —— U 盘随插随用 + 一键制作急救工具盘。

场景（课堂一体机）：
  一体机系统崩了、或被学生装了一堆东西，连 OpenClass-Box 自己都打不开。
  维修老师带个 U 盘过来，插上直接跑工具箱做诊断与修复。

这里做两件事：
  1. **便携运行**：程序放在可移动介质（U 盘）上时，数据目录固定写在
     U 盘的 OpenClass-Box\\data 里 —— 插到哪台机器都是同一套设置，
     拔走不留痕迹（不会污染对方机器的用户目录）；
  2. **一键制作急救盘**：把精简后的程序复制到 U 盘（排除 OpenOffice /
     VLC / mpv 等重型工具，保持轻量），并写入使用说明与启动脚本。
"""
from __future__ import annotations

import ctypes
import os
import shutil
import string
from pathlib import Path
from typing import Any, Callable

from .paths import app_root

ProgressCallback = Callable[[str, int], None]

# 制作急救盘时排除的内容：重型工具与开发产物，保持 U 盘轻量
_EXCLUDE_TOP = (
    "data",
    "dist_build",
    "build_build",
    "installer",
    "signing",
    ".git",
    ".github",
    "__pycache__",
    "node_modules",
)
_EXCLUDE_TOOLS = (
    "openoffice",
    "libreoffice",
    "vlc",
    "mpv",
)

_README = """OpenClass-Box 便携急救盘
=================================

这是什么
  一个免安装的电脑急救与诊断工具箱。U 盘插上就能用，不需要在对方电脑上
  安装任何东西；带走 U 盘后，对方电脑上不会留下配置与记录。

怎么用
  1. 把 U 盘插到出问题的电脑上；
  2. 双击 U 盘根目录的「启动OpenClass-Box.bat」；
  3. 打开后常用入口：
     · 维护      —— 一键体检、修复（DNS / 临时文件 / 音频服务 / 网络重置）、
                    磁盘清理、网络诊断
     · 诊断      —— 一键生成诊断包（系统信息 + 事件日志），可交给报修人员
     · 硬件信息  —— CPU / 显卡 / 内存 / 硬盘 / 主板 / 温度实测
     · 机房管理  —— 需要时把本机临时设为 B 端，接入老师的 A 端

数据写在哪里
  全部写在 U 盘里的 data 目录（配置、安全记录、收发文件），
  不会写到对方电脑的系统盘。

注意
  · 结束进程、修复网络、创建还原点等操作需要管理员权限，
    请右键「以管理员身份运行」；
  · 建议使用 USB 3.0 及以上接口，启动更快；
  · 本盘不含 OpenOffice / VLC 等大型工具（保持轻量），
    需要时请使用完整安装包或 B 端版本。
"""

_BAT = """@echo off
chcp 936 >nul
title OpenClass-Box 便携工具箱
echo 正在启动 OpenClass-Box（便携模式）...
start "" "%~dp0OpenClass-Box\\OpenClass-Box.exe"
exit
"""


def drive_type(letter: str) -> int:
    """盘符类型：2=可移动，3=固定盘，4=网络，5=光驱，0=未知。"""
    if os.name != "nt":
        return 0
    try:
        return int(ctypes.windll.kernel32.GetDriveTypeW(f"{letter.rstrip(':')}:\\"))
    except (AttributeError, OSError):
        return 0


def is_portable_media(path: Path | None = None) -> bool:
    """程序当前是否运行在可移动介质（U 盘）上。"""
    target = path or app_root()
    try:
        drive = target.resolve().drive or ""
    except OSError:
        drive = target.drive or ""
    if not drive:
        return False
    return drive_type(drive) == 2


def list_removable_drives() -> list[dict[str, Any]]:
    """列出当前接入的可移动磁盘（U 盘 / 移动硬盘）。"""
    drives: list[dict[str, Any]] = []
    if os.name != "nt":
        return drives
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if not os.path.exists(root):
            continue
        kind = drive_type(letter)
        if kind != 2:
            continue
        item: dict[str, Any] = {"drive": f"{letter}:", "root": root, "total": 0, "free": 0}
        try:
            usage = shutil.disk_usage(root)
            item["total"] = usage.total
            item["free"] = usage.free
        except OSError:
            pass
        drives.append(item)
    return drives


def portable_status() -> dict[str, Any]:
    """便携状态：是否在 U 盘上运行 + 数据目录位置。"""
    from .paths import data_root

    media = is_portable_media()
    return {
        "portable": media,
        "dataDir": str(data_root()),
        "appRoot": str(app_root()),
        "removable": list_removable_drives(),
    }


def _ignore_factory(source: Path):
    include_tools = {name for name in _EXCLUDE_TOOLS}

    def _ignore(directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        try:
            relative = Path(directory).resolve().relative_to(source.resolve())
        except (OSError, ValueError):
            relative = Path(".")
        prefix = "" if relative == Path(".") else relative.as_posix()
        for name in names:
            full = name if not prefix else f"{prefix}/{name}"
            if not prefix and name in _EXCLUDE_TOP:
                ignored.add(name)
                continue
            if name == "__pycache__":
                ignored.add(name)
                continue
            if prefix == "tools" and name in include_tools:
                ignored.add(name)
                continue
        return ignored

    return _ignore


def make_rescue_usb(drive: str, progress: ProgressCallback | None = None) -> dict[str, Any]:
    """把当前程序精简复制到指定 U 盘，做成便携急救盘。"""

    def notify(text: str, percent: int) -> None:
        if progress is not None:
            try:
                progress(text, percent)
            except Exception:
                pass

    letter = (drive or "").rstrip(":").rstrip("\\").strip().upper()
    if len(letter) != 1 or not letter.isalpha():
        return {"ok": False, "message": "请选择有效的盘符"}
    if drive_type(letter) != 2:
        return {"ok": False, "message": "目标不是可移动磁盘（U 盘 / 移动硬盘）"}

    root = Path(f"{letter}:\\") if os.name == "nt" else Path(f"/{letter}")
    source = app_root()
    target = root / "OpenClass-Box"

    try:
        usage = shutil.disk_usage(str(root))
    except OSError as exc:
        return {"ok": False, "message": f"无法访问该磁盘：{exc}"}

    # 粗估：程序目录大小 × 0.6（排除重型工具后），并留 200MB 余量
    try:
        need = int(sum(f.stat().st_size for f in source.rglob("*") if f.is_file()) * 0.6)
    except OSError:
        need = 0
    if usage.free < need + 200 * 1024 * 1024:
        return {
            "ok": False,
            "message": f"U 盘剩余空间不足（需约 {(need + 200 * 1024 * 1024) / 1048576:.0f} MB）",
        }

    notify("正在复制程序文件…", 8)
    try:
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, ignore=_ignore_factory(source), dirs_exist_ok=True)
    except OSError as exc:
        return {"ok": False, "message": f"复制失败：{exc}"}

    notify("正在写入使用说明…", 88)
    try:
        (target / "使用说明.txt").write_text(_README, encoding="utf-8")
        # 批处理用 GBK：cmd 默认代码页是 936，用 UTF-8 会显示乱码
        (root / "启动OpenClass-Box.bat").write_text(_BAT, encoding="gbk", errors="ignore")
        (target / "data").mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"ok": False, "message": f"写入说明失败：{exc}"}

    notify("完成", 100)
    return {
        "ok": True,
        "message": f"急救盘制作完成：{target}",
        "path": str(target),
        "drive": f"{letter}:",
    }
