"""
网络诊断 —— 课堂一体机断网时的分步排查。

思路：老师不需要懂技术，只要看到「哪一步不通」即可判断问题范围：
  1. 本机网卡是否有有效地址
  2. 能否 ping 通网关（局域网是否通）
  3. 能否解析域名（DNS 是否正常）
  4. 能否连通外网（互联网是否通）

全部使用系统自带命令与真实查询，不依赖第三方服务；每步都有超时保护。
"""
from __future__ import annotations

import socket
import subprocess
from typing import Any

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

try:
    import psutil
except ImportError:
    psutil = None


def _ping(host: str, timeout_ms: int = 1500) -> bool:
    """ping 指定主机（Windows 自带 ping）。"""
    try:
        proc = subprocess.run(
            ["ping", "-n", "2", "-w", str(timeout_ms), host],
            capture_output=True,
            timeout=8,
            creationflags=_CREATE_NO_WINDOW,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _gateways() -> list[str]:
    """从路由表提取默认网关（真实数据）。"""
    found: list[str] = []
    try:
        proc = subprocess.run(
            ["route", "print", "0.0.0.0"],
            capture_output=True,
            timeout=8,
            creationflags=_CREATE_NO_WINDOW,
        )
        for line in proc.stdout.decode("gbk", "ignore").splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                gateway = parts[2]
                if gateway not in found and gateway != "在链路上":
                    found.append(gateway)
    except (OSError, subprocess.SubprocessError):
        pass
    return found


def _local_ipv4() -> list[str]:
    """本机活动网卡的 IPv4。"""
    addresses: list[str] = []
    if psutil:
        try:
            for name, stat in psutil.net_if_stats().items():
                if not stat.isup:
                    continue
                for addr in psutil.net_if_addrs().get(name, []):
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        addresses.append(f"{name}={addr.address}")
        except OSError:
            pass
    return addresses


def _dns_ok() -> bool:
    """域名解析是否正常（真实解析，不访问外网内容）。"""
    try:
        socket.getaddrinfo("www.baidu.com", 443, socket.AF_INET)
        return True
    except OSError:
        return False


def run_diagnostics() -> dict[str, Any]:
    """执行分步网络诊断，返回每步的真实结果。

    注意：不少路由器/网关禁用 ICMP，ping 不通网关但网络完全正常；
    因此「局域网」一项会结合外网结果判断，避免把正常网络误报成故障。
    """
    # 先取客观事实
    addresses = _local_ipv4()
    dns_ok = _dns_ok()
    internet_ok = _ping("223.5.5.5", 2000) if dns_ok else False
    gateways = _gateways()
    gateway_reachable = any(_ping(gw) for gw in gateways) if gateways else False

    items: list[dict[str, Any]] = []

    # 1) 本机地址
    items.append(
        {
            "name": "本机网络地址",
            "ok": bool(addresses),
            "detail": "，".join(addresses) if addresses else "没有检测到有效的 IPv4 地址",
            "suggest": "" if addresses else "网线/无线未连接，或网卡被禁用",
        }
    )

    # 2) 局域网（网关）—— 网关禁 ping 时以「外网可达」为准
    if not gateways:
        items.append(
            {
                "name": "局域网（网关）",
                "ok": False,
                "detail": "未获取到默认网关",
                "suggest": "网络未正确配置，可尝试「一键修复 → 重置网络」",
            }
        )
    elif gateway_reachable:
        items.append(
            {
                "name": "局域网（网关）",
                "ok": True,
                "detail": f"网关 {'、'.join(gateways)} 可达",
                "suggest": "",
            }
        )
    elif internet_ok:
        items.append(
            {
                "name": "局域网（网关）",
                "ok": True,
                "detail": (
                    f"网关 {'、'.join(gateways)} 未响应 ping"
                    "（部分路由设备会禁用），但网络访问正常"
                ),
                "suggest": "",
            }
        )
    else:
        items.append(
            {
                "name": "局域网（网关）",
                "ok": False,
                "detail": f"网关 {'、'.join(gateways)} 不可达",
                "suggest": "检查网线、交换机或无线连接",
            }
        )

    # 3) DNS
    items.append(
        {
            "name": "域名解析（DNS）",
            "ok": dns_ok,
            "detail": "域名可正常解析" if dns_ok else "域名无法解析",
            "suggest": "" if dns_ok else "DNS 异常，可尝试「一键修复 → 清理 DNS 缓存」",
        }
    )

    # 4) 外网连通
    items.append(
        {
            "name": "外网连通",
            "ok": internet_ok,
            "detail": "可以访问互联网" if internet_ok else "无法连通外网",
            "suggest": "" if internet_ok else "若局域网正常，可能是宽带或路由问题，请联系网络管理员",
        }
    )

    ok_count = sum(1 for item in items if item["ok"])
    return {"items": items, "okCount": ok_count, "total": len(items), "healthy": ok_count == len(items)}
