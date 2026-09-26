"""
诊断日志采集 —— 一键把系统日志与设备信息打包，便于远程报修。

产出：桌面上一个 zip 诊断包，内含：
  - system-info.txt                     本机硬件/系统信息（真实采集）
  - health.txt                          体检结果
  - event-application.txt / event-system.txt   最近的系统事件日志

原则：只读不写系统；单项采集失败只记录说明，不中断整包生成。
"""
from __future__ import annotations

import datetime as _dt
import os
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from .health import run_checks
from .report import collect as collect_system, render_text

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_PS = ["powershell", "-NoProfile", "-Command"]
_MAX_EVENTS = 300


def _decode(raw: bytes) -> str:
    """PowerShell 输出解码：优先 UTF-8，回退 GBK。"""
    for encoding in ("utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def _event_log_text(name: str) -> str:
    """导出最近的事件日志为文本（只读）。"""
    script = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        f"Get-WinEvent -LogName {name} -MaxEvents {_MAX_EVENTS} -ErrorAction SilentlyContinue | "
        "Select-Object TimeCreated,LevelDisplayName,ProviderName,Id,Message | "
        "Format-List | Out-String -Width 300"
    )
    try:
        proc = subprocess.run(
            [*_PS, script], capture_output=True, timeout=150, creationflags=_CREATE_NO_WINDOW
        )
        text = _decode(proc.stdout).strip()
        return text or f"（未能读取 {name} 日志：可能被组策略限制）"
    except (OSError, subprocess.SubprocessError) as exc:
        return f"（读取 {name} 日志失败：{exc}）"


def export() -> dict[str, Any]:
    """生成诊断包到桌面，返回 {ok, path, size, parts, message}。"""
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    desktop = Path(os.path.expanduser("~")) / "Desktop"
    if not desktop.is_dir():
        desktop = Path(os.path.expanduser("~"))
    zip_path = desktop / f"OpenClass-Box诊断包_{stamp}.zip"

    parts: list[str] = []
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            # 1) 系统信息
            try:
                archive.writestr("system-info.txt", render_text(collect_system()))
                parts.append("系统信息")
            except (OSError, ValueError) as exc:
                archive.writestr("system-info.txt", f"采集失败：{exc}")

            # 2) 体检结果
            try:
                health = run_checks()
                lines = [
                    f"{'正常' if item['ok'] else '异常'}｜{item['name']}：{item['detail']}"
                    for item in health["items"]
                ]
                archive.writestr("health.txt", "\n".join(lines))
                parts.append("体检结果")
            except (OSError, ValueError) as exc:
                archive.writestr("health.txt", f"采集失败：{exc}")

            # 3) 事件日志
            for log_name, file_name in (
                ("Application", "event-application.txt"),
                ("System", "event-system.txt"),
            ):
                archive.writestr(file_name, _event_log_text(log_name))
                parts.append(f"{log_name} 日志")

        size = zip_path.stat().st_size
        return {
            "ok": True,
            "path": str(zip_path),
            "size": size,
            "parts": parts,
            "message": "诊断包已生成",
        }
    except (OSError, zipfile.BadZipFile) as exc:
        return {"ok": False, "path": "", "size": 0, "parts": parts, "message": f"生成失败：{exc}"}
