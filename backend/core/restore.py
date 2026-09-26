"""
系统还原点 —— 查看与创建（创建需要管理员权限，走 UAC 确认）。

课堂场景：电教在装软件/改设置之前先建一个还原点，出问题可以回滚。
注意：Windows 对还原点有频率限制（默认 24 小时内只允许创建一个），
这是系统行为，本工具如实反馈系统返回的信息。
"""
from __future__ import annotations

import ctypes
import json
import subprocess
from typing import Any

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_PS = ["powershell", "-NoProfile", "-Command"]


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _run_elevated(command: str) -> bool:
    """以管理员身份运行 PowerShell（弹 UAC）。"""
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "powershell.exe", f'-NoProfile -Command "{command}"', None, 1
        )
        return int(rc) > 32
    except (AttributeError, OSError):
        return False


def list_points() -> dict[str, Any]:
    """列出系统还原点（只读查询）。"""
    script = (
        "Get-ComputerRestorePoint | "
        "Select-Object SequenceNumber,Description,CreationTime | "
        "ConvertTo-Json -Compress"
    )
    try:
        proc = subprocess.run(
            [*_PS, script], capture_output=True, timeout=60, creationflags=_CREATE_NO_WINDOW
        )
        text = proc.stdout.decode("gbk", "ignore").strip()
        if not text:
            return {"ok": True, "points": [], "message": "当前没有可用的还原点"}
        data = json.loads(text)
        points = data if isinstance(data, list) else [data]
        return {"ok": True, "points": points, "message": ""}
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {"ok": False, "points": [], "message": f"读取失败：{exc}"}


def create_point(description: str = "") -> dict[str, Any]:
    """创建系统还原点（需要管理员权限）。"""
    # 描述只保留安全字符，避免命令注入
    desc = "".join(ch for ch in (description or "OpenClass-Box 手动还原点") if ch.isalnum() or ch in "-_ 中文")[:60]
    if not desc:
        desc = "OpenClass-Box 手动还原点"

    command = f"Checkpoint-Computer -Description '{desc}' -RestorePointType 'MODIFY_SETTINGS'"

    if _is_admin():
        try:
            proc = subprocess.run(
                [*_PS, command], capture_output=True, timeout=180, creationflags=_CREATE_NO_WINDOW
            )
            if proc.returncode == 0:
                return {"ok": True, "message": "还原点创建成功"}
            err = proc.stderr.decode("gbk", "ignore").strip()[:200]
            return {"ok": False, "message": f"创建失败：{err or '系统拒绝了本次操作'}"}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "message": f"创建失败：{exc}"}

    ok = _run_elevated(command)
    return {
        "ok": ok,
        "message": "已请求管理员权限创建还原点（请在系统弹窗中确认）" if ok else "提权被取消或失败",
    }
