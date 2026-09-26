"""
硬件详情采集 —— CPU / 显卡 / 内存 / 硬盘 / 主板 / 温度。

数据全部来自本机真实查询（注册表 + CIM/WMI + psutil）。
**任何拿不到的项一律返回 None，前端显示"不可用"，绝不编造数值。**

性能设计（解决"采集慢 / 采集不到"）：
  1. 注册表读取显存是**秒级**的，先给出「快速快照」，界面立刻有内容；
  2. WMI 详细查询拆成两段并发执行（基础信息 + 存储/温度），耗时取较长者；
  3. 完整结果后台缓存，前端轮询到 fullReady=true 再替换展示。

关键点：
  - 显存必须读注册表 HardwareInformation.qwMemorySize：
    Win32_VideoController.AdapterRAM 是 32 位字段，8GB 显卡会被截断成 4GB。
  - 温度优先 ACPI 热区；读不到就是 None（需要额外内核驱动才能读）。
"""
from __future__ import annotations

import json
import platform
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_GPU_CLASS_GUID = (
    r"SYSTEM\CurrentControlSet\Control\Class"
    r"\{4d36e968-e325-11ce-bfc1-08002be10318}"
)

# 基础信息（GPU / 主板 / BIOS / 内存条）—— 相对快
_BASE_SCRIPT = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$gpus = Get-CimInstance Win32_VideoController | ForEach-Object {
    [ordered]@{
        name = $_.Name
        adapterRAM = [int64]$_.AdapterRAM
        driverVersion = $_.DriverVersion
        driverDate = if ($_.DriverDate) { $_.DriverDate.ToString('yyyy-MM-dd') } else { '' }
        resolution = if ($_.CurrentHorizontalResolution) { "$($_.CurrentHorizontalResolution)x$($_.CurrentVerticalResolution)" } else { '' }
    }
}
$board = Get-CimInstance Win32_BaseBoard | ForEach-Object {
    [ordered]@{ manufacturer = $_.Manufacturer; product = $_.Product }
}
$bios = Get-CimInstance Win32_BIOS | ForEach-Object {
    [ordered]@{
        vendor = $_.Manufacturer
        version = $_.SMBIOSBIOSVersion
        date = if ($_.ReleaseDate) { $_.ReleaseDate.ToString('yyyy-MM-dd') } else { '' }
    }
}
$mems = Get-CimInstance Win32_PhysicalMemory | ForEach-Object {
    [ordered]@{
        capacityGB = [math]::Round($_.Capacity / 1GB, 1)
        speed = if ($_.ConfiguredClockSpeed) { $_.ConfiguredClockSpeed } else { $_.Speed }
        manufacturer = "$($_.Manufacturer)".Trim()
        slot = "$($_.DeviceLocator)".Trim()
        partNumber = "$($_.PartNumber)".Trim()
    }
}
[ordered]@{
    gpus = @($gpus)
    boards = @($board)
    bios = @($bios)
    memModules = @($mems)
} | ConvertTo-Json -Depth 6 -Compress
"""

# 存储与温度 —— 可能较慢（S.M.A.R.T. 查询）
_STORAGE_SCRIPT = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$disks = @()
try {
    $disks = Get-PhysicalDisk | ForEach-Object {
        $temp = $null
        try { $temp = (Get-StorageReliabilityCounter -PhysicalDisk $_ -ErrorAction Stop).Temperature } catch {}
        [ordered]@{
            model = $_.FriendlyName
            sizeGB = [math]::Round($_.Size / 1GB, 1)
            media = "$($_.MediaType)"
            bus = "$($_.BusType)"
            health = "$($_.HealthStatus)"
            temperature = $temp
        }
    }
} catch {}
$cpuTemp = $null
$tempSource = ''
try {
    $tz = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop
    if ($tz) {
        $cpuTemp = [math]::Round(($tz | Select-Object -First 1).CurrentTemperature / 10 - 273.15, 1)
        $tempSource = 'ACPI 热区'
    }
} catch {}
[ordered]@{
    physicalDisks = @($disks)
    cpuTemp = $cpuTemp
    tempSource = $tempSource
} | ConvertTo-Json -Depth 6 -Compress
"""


def _run_ps(script: str, timeout: float = 25) -> str:
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    raw = proc.stdout or b""
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "ignore")


def _json(script: str, timeout: float = 25) -> dict[str, Any]:
    output = _run_ps(script, timeout)
    if not output.strip():
        return {}
    start, end = output.find("{"), output.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(output[start:end])
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def gpu_vram_from_registry() -> dict[str, int]:
    """读取每张显卡的真实显存（字节），键为显卡描述名。

    这是唯一能正确反映 4GB 以上显存的可靠来源；AdapterRAM 会截断。
    """
    result: dict[str, int] = {}
    if platform.system() != "Windows":
        return result
    try:
        import winreg
    except ImportError:
        return result

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _GPU_CLASS_GUID) as root:
            index = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                if not sub.isdigit():
                    continue
                try:
                    with winreg.OpenKey(root, sub) as key:
                        desc = str(winreg.QueryValueEx(key, "DriverDesc")[0])
                        size = 0
                        for value_name in (
                            "HardwareInformation.qwMemorySize",
                            "HardwareInformation.MemorySize",
                        ):
                            try:
                                size = int(winreg.QueryValueEx(key, value_name)[0])
                                break
                            except OSError:
                                continue
                        if size > 0:
                            result[desc] = max(result.get(desc, 0), size)
                except OSError:
                    continue
    except OSError:
        pass
    return result


# ══════════════════════════════════════════════════════════════
# 采集与缓存（快速快照 + 后台完整）
# ══════════════════════════════════════════════════════════════

_lock = threading.Lock()
_full_cache: dict[str, Any] | None = None
_full_started = False


def _quick_snapshot() -> dict[str, Any]:
    """秒级快照：仅注册表显存（慢查询一律留空）。"""
    gpus: list[dict[str, Any]] = []
    try:
        for name, size in gpu_vram_from_registry().items():
            gpus.append(
                {
                    "name": name,
                    "memoryGB": round(size / (1024 ** 3), 1),
                    "driverVersion": "",
                    "driverDate": "",
                    "resolution": "",
                }
            )
    except Exception:
        gpus = []
    return {
        "gpus": gpus,
        "boards": [],
        "bios": [],
        "memModules": [],
        "physicalDisks": [],
        "cpuTemp": None,
        "tempSource": "",
        "vramSource": "registry",
        "fullReady": False,
    }


def _collect_full() -> dict[str, Any]:
    """完整采集：两段 PowerShell 脚本并发执行 + 注册表显存修正。"""
    base: dict[str, Any] = {}
    storage: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        base_future = pool.submit(_json, _BASE_SCRIPT, 25)
        storage_future = pool.submit(_json, _STORAGE_SCRIPT, 25)
        try:
            base = base_future.result(timeout=30)
        except Exception:
            base = {}
        try:
            storage = storage_future.result(timeout=30)
        except Exception:
            storage = {}

    vram = gpu_vram_from_registry()
    gpus: list[dict[str, Any]] = []
    for item in base.get("gpus", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        memory = int(item.get("adapterRAM") or 0)
        if name in vram and vram[name] > memory:
            memory = vram[name]
        gpus.append(
            {
                "name": name,
                "memoryGB": round(memory / (1024 ** 3), 1) if memory else None,
                "driverVersion": item.get("driverVersion") or "",
                "driverDate": item.get("driverDate") or "",
                "resolution": item.get("resolution") or "",
            }
        )
    # 注册表读到但 WMI 未报告的显卡也补上（其显存最准）
    known = {g["name"] for g in gpus}
    for name, size in vram.items():
        if name not in known:
            gpus.append(
                {
                    "name": name,
                    "memoryGB": round(size / (1024 ** 3), 1),
                    "driverVersion": "",
                    "driverDate": "",
                    "resolution": "",
                }
            )

    return {
        "gpus": gpus,
        "boards": [b for b in (base.get("boards", []) or []) if isinstance(b, dict)],
        "bios": [b for b in (base.get("bios", []) or []) if isinstance(b, dict)],
        "memModules": [m for m in (base.get("memModules", []) or []) if isinstance(m, dict)],
        "physicalDisks": [
            d for d in (storage.get("physicalDisks", []) or []) if isinstance(d, dict)
        ],
        "cpuTemp": storage.get("cpuTemp"),
        "tempSource": storage.get("tempSource") or "",
        "vramSource": "registry" if vram else "wmi",
        "fullReady": True,
    }


def _start_full() -> None:
    """后台启动完整采集（幂等）。"""
    global _full_started
    with _lock:
        if _full_started:
            return
        _full_started = True

    def _work() -> None:
        global _full_cache
        try:
            data = _collect_full()
        except Exception:
            data = _quick_snapshot()
            data["fullReady"] = True
        with _lock:
            _full_cache = data

    threading.Thread(target=_work, daemon=True, name="oc-hw-detail").start()


def collect(quick: bool = False) -> dict[str, Any]:
    """返回硬件详情。

    quick=True  → 立刻返回秒级快照（并触发后台完整采集）
    默认        → 完整数据已就绪则返回完整；否则返回快照并继续后台采集
    """
    with _lock:
        cached = _full_cache
    if cached is not None:
        return cached

    snapshot = _quick_snapshot()
    if not quick:
        _start_full()
    else:
        _start_full()
    return snapshot
