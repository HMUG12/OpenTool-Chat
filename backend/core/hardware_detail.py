"""
硬件详情采集 —— CPU / 显卡 / 内存 / 硬盘 / 主板 / 温度。

数据全部来自本机真实查询（注册表 + CIM/WMI + psutil）。
**任何拿不到的项一律返回 None，前端显示"不可用"，绝不编造数值。**

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
from typing import Any

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_GPU_CLASS_GUID = (
    r"SYSTEM\CurrentControlSet\Control\Class"
    r"\{4d36e968-e325-11ce-bfc1-08002be10318}"
)

_SENSOR_SCRIPT = r"""
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
    gpus = @($gpus)
    boards = @($board)
    bios = @($bios)
    memModules = @($mems)
    physicalDisks = @($disks)
    cpuTemp = $cpuTemp
    tempSource = $tempSource
} | ConvertTo-Json -Depth 6 -Compress
"""


def _run_ps(script: str, timeout: float = 30) -> str:
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


def _json(script: str, timeout: float = 30) -> dict[str, Any]:
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


_cache_lock = threading.Lock()
_cached: dict[str, Any] | None = None


def collect(force: bool = False) -> dict[str, Any]:
    """采集详细硬件信息（一次 PowerShell 调用取全，结果缓存）。"""
    global _cached
    with _cache_lock:
        if _cached is not None and not force:
            return _cached

    data = _json(_SENSOR_SCRIPT)

    # 显存修正：注册表 qwMemorySize 优先于会被截断的 AdapterRAM
    vram = gpu_vram_from_registry()
    gpus: list[dict[str, Any]] = []
    for item in data.get("gpus", []) or []:
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

    result = {
        "gpus": gpus,
        "boards": [b for b in (data.get("boards", []) or []) if isinstance(b, dict)],
        "bios": [b for b in (data.get("bios", []) or []) if isinstance(b, dict)],
        "memModules": [m for m in (data.get("memModules", []) or []) if isinstance(m, dict)],
        "physicalDisks": [d for d in (data.get("physicalDisks", []) or []) if isinstance(d, dict)],
        "cpuTemp": data.get("cpuTemp"),
        "tempSource": data.get("tempSource") or "",
        "vramSource": "registry" if vram else "wmi",
    }
    with _cache_lock:
        _cached = result
    return result
