"""
一键修复 —— 课堂一体机常见故障的修复动作。

原则：
  - 每个动作只使用**固定的系统命令**，不拼接任何外部输入；
  - 需要管理员的动作明确标注，执行时走 UAC 提权（用户确认后才执行）；
  - 只回报「成功 / 失败 / 需要重启」，不夸大结果。
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# mode: cmd → 直接跑命令；temp → Python 清理临时目录；shell → 需要管理员，走提权
REPAIRS: list[dict[str, Any]] = [
    {
        "key": "flush_dns",
        "name": "清理 DNS 缓存",
        "desc": "网页打不开、时通时断时先做这个，不影响正在使用的软件",
        "admin": False,
        "restart": False,
        "mode": "cmd",
        "cmd": ["ipconfig", "/flushdns"],
    },
    {
        "key": "clean_temp",
        "name": "清理临时文件",
        "desc": "清空当前用户的临时目录，释放磁盘空间",
        "admin": False,
        "restart": False,
        "mode": "temp",
    },
    {
        "key": "restart_audio",
        "name": "重启音频服务",
        "desc": "没声音时使用；需要管理员权限（会弹出系统确认框）",
        "admin": True,
        "restart": False,
        "mode": "shell",
        "cmdline": "net stop Audiosrv & net start Audiosrv & net stop AudioEndpointBuilder & net start AudioEndpointBuilder",
    },
    {
        "key": "reset_network",
        "name": "重置网络",
        "desc": "网络异常时的强力修复；需要管理员权限，执行后建议重启电脑",
        "admin": True,
        "restart": True,
        "mode": "shell",
        "cmdline": "netsh winsock reset & netsh int ip reset & ipconfig /flushdns",
    },
]


def list_repairs() -> list[dict[str, Any]]:
    """列出可用修复项（不含命令细节）。"""
    return [
        {
            "key": r["key"],
            "name": r["name"],
            "desc": r["desc"],
            "admin": r["admin"],
            "restart": r["restart"],
        }
        for r in REPAIRS
    ]


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _run_elevated(cmdline: str) -> bool:
    """以管理员身份执行（弹 UAC，用户确认后运行）。"""
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {cmdline}", None, 1)
        return int(rc) > 32
    except (AttributeError, OSError):
        return False


def _clean_temp() -> tuple[bool, str]:
    """清理当前用户临时目录（被占用的文件自动跳过）。"""
    temp = Path(os.environ.get("TEMP", ""))
    if not temp.is_dir():
        return False, "未找到临时目录"

    removed = skipped = 0
    for item in temp.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink()
            removed += 1
        except OSError:
            skipped += 1
    return True, f"已清理 {removed} 项，{skipped} 项被占用跳过"


def run_repair(key: str) -> dict[str, Any]:
    """执行一个修复动作，返回 {ok, message, restart}。"""
    spec = next((r for r in REPAIRS if r["key"] == key), None)
    if spec is None:
        return {"ok": False, "message": "未知的修复项", "restart": False}

    if spec["mode"] == "temp":
        ok, message = _clean_temp()
        return {"ok": ok, "message": message, "restart": False}

    if spec["mode"] == "shell":
        if _is_admin():
            try:
                proc = subprocess.run(
                    ["cmd", "/c", spec["cmdline"]],
                    capture_output=True,
                    timeout=90,
                    creationflags=_CREATE_NO_WINDOW,
                )
                ok = proc.returncode == 0
            except (OSError, subprocess.SubprocessError):
                ok = False
            return {
                "ok": ok,
                "message": "执行完成" if ok else "执行失败（部分步骤可能未成功）",
                "restart": spec["restart"],
            }
        # 非管理员 → 提权执行
        ok = _run_elevated(spec["cmdline"])
        return {
            "ok": ok,
            "message": "已请求管理员权限，请在系统弹窗中确认" if ok else "提权被取消或失败",
            "restart": spec["restart"],
        }

    # mode == cmd
    try:
        proc = subprocess.run(
            spec["cmd"], capture_output=True, timeout=60, creationflags=_CREATE_NO_WINDOW
        )
        ok = proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    return {
        "ok": ok,
        "message": "执行完成" if ok else "执行失败",
        "restart": spec["restart"],
    }
