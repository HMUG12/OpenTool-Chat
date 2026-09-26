"""
进程 / 服务 / 启动项 —— 排障用的系统视图。

安全原则：
  - 默认只读展示，数据均为本机实时查询；
  - 结束进程必须显式传入 pid，且**拒绝系统关键进程**（防止把系统搞崩）；
  - 不提供任何"一键优化/一键加速"式的危险批量操作。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

# 结束这些进程会导致系统不稳定，直接拒绝
PROTECTED = {
    "system", "registry", "memory compression",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "fontdrvhost.exe",
    "dwm.exe", "svchost.exe", "audiodg.exe",
}


def list_processes(limit: int = 40) -> dict[str, Any]:
    """按内存占用列出进程（前 N 名）。"""
    if not psutil:
        return {"items": [], "total": 0}

    rows: list[dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "username", "memory_info"]):
        try:
            info = proc.info
            memory = info.get("memory_info")
            rows.append(
                {
                    "pid": info.get("pid"),
                    "name": info.get("name") or "?",
                    "user": (info.get("username") or "").split("\\")[-1],
                    "memoryMB": round((memory.rss if memory else 0) / 1048576, 1),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    rows.sort(key=lambda row: row["memoryMB"], reverse=True)
    return {"items": rows[: max(1, limit)], "total": len(rows)}


def kill_process(pid: int) -> dict[str, Any]:
    """结束指定进程（系统关键进程一律拒绝）。"""
    if not psutil:
        return {"ok": False, "message": "psutil 不可用"}
    try:
        proc = psutil.Process(int(pid))
    except (psutil.NoSuchProcess, ValueError):
        return {"ok": False, "message": "进程不存在（可能已经结束）"}

    name = (proc.name() or "").lower()
    if name in PROTECTED:
        return {"ok": False, "message": f"{name} 是系统关键进程，已拒绝结束"}

    try:
        proc.terminate()
        return {"ok": True, "message": f"已请求结束 {name}（PID {pid}）"}
    except psutil.AccessDenied:
        return {"ok": False, "message": "权限不足，无法结束该进程（可尝试以管理员运行）"}
    except psutil.Error as exc:
        return {"ok": False, "message": f"结束失败：{exc}"}


def list_services(limit: int = 150) -> dict[str, Any]:
    """列出 Windows 服务（运行中的排在前面）。"""
    if not psutil:
        return {"items": [], "total": 0}

    items: list[dict[str, str]] = []
    total = 0
    try:
        for service in psutil.win_service_iter():
            total += 1
            if len(items) >= limit:
                continue
            try:
                info = service.as_dict()
                items.append(
                    {
                        "name": str(info.get("name", "")),
                        "display": str(info.get("display_name", "")),
                        "status": str(info.get("status", "")),
                        "startType": str(info.get("start_type", "")),
                    }
                )
            except psutil.Error:
                continue
    except (OSError, psutil.Error):
        pass

    items.sort(key=lambda item: (item["status"] != "running", item["name"]))
    return {"items": items, "total": total}


def list_startup() -> dict[str, Any]:
    """列出开机启动项（注册表 Run 键 + 启动文件夹）。"""
    items: list[dict[str, str]] = []

    try:
        import winreg

        keys = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "注册表/当前用户"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "注册表/所有用户"),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
                "注册表/所有用户(32位)",
            ),
        ]
        for root, path, source in keys:
            try:
                with winreg.OpenKey(root, path) as key:
                    index = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, index)
                        except OSError:
                            break
                        items.append(
                            {"name": name, "command": str(value), "source": source}
                        )
                        index += 1
            except OSError:
                continue
    except ImportError:
        pass

    folders = [
        (
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft/Windows/Start Menu/Programs/Startup",
            "启动文件夹/当前用户",
        ),
        (
            Path(os.environ.get("ProgramData", ""))
            / "Microsoft/Windows/Start Menu/Programs/Startup",
            "启动文件夹/所有用户",
        ),
    ]
    for folder, source in folders:
        try:
            if folder.is_dir():
                for entry in folder.iterdir():
                    if entry.name.lower() == "desktop.ini":
                        continue
                    items.append({"name": entry.stem, "command": str(entry), "source": source})
        except OSError:
            continue

    return {"items": items, "total": len(items)}
