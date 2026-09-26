"""
报修报告 —— 一键导出本机真实信息，供维修人员快速判断问题。

原则：
  - 内容全部来自真实系统查询（psutil / platform），**不编造任何字段**；
  - 输出纯文本（UTF-8），默认存到桌面，便于发送或打印；
  - 失败时明确返回错误，不产出半份报告。
"""
from __future__ import annotations

import datetime as _dt
import os
import platform
import socket
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

from .health import run_checks


def _gb(value: float) -> str:
    return f"{value / 1024 ** 3:.1f} GB"


def _cpu_processor_name() -> str:
    """从注册表取 CPU 型号（platform.processor 在部分机器上为空）。"""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        ) as key:
            return str(winreg.QueryValueEx(key, "ProcessorNameString")[0])
    except (OSError, ImportError):
        return platform.processor() or "-"


def collect() -> dict[str, Any]:
    """采集本机信息（全部真实查询）。"""
    data: dict[str, Any] = {
        "生成时间": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "系统": {
            "版本": f"{platform.system()} {platform.release()}",
            "内部版本": platform.version(),
            "计算机名": socket.gethostname(),
            "处理器架构": platform.machine(),
        },
    }

    if psutil:
        freq = psutil.cpu_freq()
        data["CPU"] = {
            "型号": _cpu_processor_name(),
            "物理核心 / 逻辑核心": f"{psutil.cpu_count(logical=False)} / {psutil.cpu_count(logical=True)}",
            "当前频率": f"{freq.current:.0f} MHz" if freq else "-",
            "当前占用": f"{psutil.cpu_percent(interval=0.4):.0f}%",
        }

        mem = psutil.virtual_memory()
        data["内存"] = {
            "总量": _gb(mem.total),
            "已用": f"{_gb(mem.used)}（{mem.percent:.0f}%）",
            "可用": _gb(mem.available),
        }

        disks: list[str] = []
        for part in psutil.disk_partitions(all=False):
            if "cdrom" in (part.opts or "") or not part.fstype:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except OSError:
                continue
            disks.append(
                f"{part.mountpoint} {part.fstype}｜总 {_gb(usage.total)} / "
                f"已用 {_gb(usage.used)}（{usage.percent:.0f}%）/ 可用 {_gb(usage.free)}"
            )
        data["磁盘"] = disks

        nets: list[str] = []
        addrs = psutil.net_if_addrs()
        for name, stat in psutil.net_if_stats().items():
            if not stat.isup:
                continue
            ipv4 = [
                a.address
                for a in addrs.get(name, [])
                if a.family == socket.AF_INET and not a.address.startswith("127.")
            ]
            if ipv4:
                nets.append(f"{name}：{', '.join(ipv4)}")
        data["网络"] = nets

    health = run_checks()
    data["体检结果"] = [
        f"{'正常' if item['ok'] else '异常'}｜{item['name']}：{item['detail']}"
        for item in health["items"]
    ]
    return data


def render_text(data: dict[str, Any]) -> str:
    """渲染为整齐的纯文本报告。"""
    lines = ["=" * 48, "OpenClass-Box 报修信息报告", "=" * 48]

    for key, value in data.items():
        if key == "生成时间":
            continue
        lines.append("")
        lines.append(f"【{key}】")
        if isinstance(value, dict):
            for k, v in value.items():
                lines.append(f"  {k}：{v}")
        elif isinstance(value, list):
            lines.extend([f"  - {item}" for item in value] or ["  （无）"])
        else:
            lines.append(f"  {value}")

    lines += [
        "",
        "-" * 48,
        f"生成时间：{data.get('生成时间', '-')}",
        "说明：本报告由 OpenClass-Box 自动采集，内容均为本机真实信息。",
    ]
    return "\n".join(lines)


def export() -> dict[str, Any]:
    """生成报告并保存到桌面。返回 {ok, path, content}。"""
    try:
        data = collect()
        text = render_text(data)
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        if not desktop.is_dir():
            desktop = Path(os.path.expanduser("~"))
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = desktop / f"OpenClass-Box报修报告_{stamp}.txt"
        path.write_text(text, encoding="utf-8")
        return {"ok": True, "path": str(path), "content": text}
    except (OSError, ValueError) as exc:
        return {"ok": False, "path": "", "content": f"导出失败：{exc}"}
