"""
课堂兼容性知识库 —— 把「老师遇到的问题」沉淀成可复用的经验。

为什么要有它：通用工具箱只给数字（温度 78°C、磁盘 62%），但老师需要的是
「这意味着什么、我该怎么办」。市面上的集控系统有自己的知识库，但闭源且只
服务自家硬件；这里做成**离线、跨品牌、可累积、可分享**的。

三条能力：
  1. **内置条目**：随程序分发的常见课堂问题（投屏 / 触摸 / 还原 / 声音 / 卡顿…），
     标注来源与适用条件，不编造案例；
  2. **环境匹配**：读取本机实测环境（系统版本、已装教学软件、触摸/无线投屏能力、
     是否有还原保护），自动挑出「和你这台机器相关」的条目；
  3. **本地累积与分享**：把新问题导出成标准化 JSON（含环境快照），
     可以发给维护者或提 PR；导入别人分享的条目后，知识库就在本地长大。
"""
from __future__ import annotations

import json
import platform
import threading
import time
from pathlib import Path
from typing import Any

from .paths import config_dir

_KB_VERSION = "2026.09"
_lock = threading.RLock()

# ══════════════════════════════════════════════════════════════
# 内置条目（source 标注来源：通用经验 / 公开资料，绝不假装是真实案例）
# ══════════════════════════════════════════════════════════════

_ENTRIES: list[dict[str, Any]] = [
    {
        "id": "screen-no-signal",
        "category": "投屏",
        "title": "有线投屏没画面（一体机正常、投影黑屏）",
        "symptom": "一体机本身有画面，投影仪或外接屏黑屏 / 提示无信号",
        "cause": "三类最常见：① 显示模式被切到「仅电脑屏幕」或「扩展」；② HDMI/VGA 线松动、接口氧化或线材老化；③ 投影仪输入源没切到对应通道",
        "solution": "按 Win+P 选「复制」；重新插拔线缆（换一根试）；把投影仪输入源切到 HDMI1/HDMI2/VGA",
        "tags": ["投影", "投屏", "无信号", "Win+P"],
        "match": {"flags": ["multiMonitor"]},
        "source": "通用经验",
    },
    {
        "id": "screen-ratio",
        "category": "投屏",
        "title": "投影画面被拉伸变形（4:3 与 16:9 不匹配）",
        "symptom": "投影出来的画面人物变胖、圆形变椭圆",
        "cause": "一体机输出 16:9，投影仪按 4:3 显示（或反之），比例不一致",
        "solution": "把两边分辨率都设为 1920×1080（16:9），并在投影仪菜单里把「画面比例」设为 16:9 或「自动」",
        "tags": ["投影", "分辨率", "比例", "变形"],
        "source": "通用经验",
    },
    {
        "id": "wireless-no-miracast",
        "category": "投屏",
        "title": "无线投屏搜不到 / 连不上",
        "symptom": "手机或笔记本的「投影到此电脑」里找不到这台一体机",
        "cause": "无线投屏（Miracast）需要无线网卡支持 Wi-Fi Direct 且 WLAN 服务运行；不少教室一体机出厂没有无线网卡，或驱动被禁用",
        "solution": "先在「课堂」页看无线投屏检测结果：提示没有无线网卡就改用有线/投屏器；有网卡但服务停了，把 WLAN AutoConfig 服务启动并设为自动",
        "tags": ["无线投屏", "Miracast", "Wi-Fi Direct", "搜不到"],
        "match": {"flags": ["wireless"]},
        "source": "通用经验",
    },
    {
        "id": "touch-not-responding",
        "category": "触摸",
        "title": "触摸失灵或点到别的位置",
        "symptom": "手指点在 A 处，响应在 B 处；或者干脆没反应",
        "cause": "常见原因：① 触摸校准数据丢失（换显示器、更新驱动后）；② 「符合 HID 标准的触摸屏」在设备管理器里被禁用或报错；③ 屏幕表面有水渍、粉笔灰或强光干扰",
        "solution": "在「课堂」页点「触摸校准」，按十字光标依次点完；仍不行就到设备管理器把触摸屏设备禁用再启用；擦净屏幕、避开强光",
        "tags": ["触摸", "校准", "失灵", "漂移"],
        "match": {"flags": ["touch"]},
        "source": "通用经验",
    },
    {
        "id": "touch-after-driver-update",
        "category": "触摸",
        "title": "更新驱动后触摸失效",
        "symptom": "系统或驱动更新完成后，触摸屏突然不能用",
        "cause": "驱动更新覆盖了原厂触摸驱动，或触摸屏设备被重新枚举后未恢复",
        "solution": "设备管理器 → 人体学输入设备 → 卸载「符合 HID 标准的触摸屏」，重启后让系统重新识别；仍未恢复就用原厂驱动包重装",
        "tags": ["触摸", "驱动", "更新"],
        "source": "通用经验",
    },
    {
        "id": "restore-guard-revert",
        "category": "还原",
        "title": "改了设置、重启后又变回去了",
        "symptom": "装好软件或改好设置，重启后被还原成原样",
        "cause": "这台机器开启了还原保护（冰点还原 Deep Freeze / 影子系统 / 慧盾 / 云桌面），系统盘处于「重启即还原」状态",
        "solution": "先在「课堂」页确认是否检测到还原软件；要长期保留改动，需要在保护软件里解除保护（或把改动写入还原软件的「保留分区」）后再重启",
        "tags": ["还原", "冰点", "影子系统", "重启复原"],
        "match": {"flags": ["restoreGuard"]},
        "source": "通用经验",
    },
    {
        "id": "board-software-crash",
        "category": "白板软件",
        "title": "白板软件打不开课件 / 打开就闪退",
        "symptom": "双击课件没反应，或打开几秒后白板软件自动关闭",
        "cause": "多数与显卡驱动和硬件加速有关（尤其是集显 + 旧驱动），也可能是课件文件损坏、软件版本过旧",
        "solution": "先把显卡驱动更新到厂商版本；再在白板软件的设置里关掉「硬件加速」；换一个课件文件测试，确认是不是单个文件的问题",
        "tags": ["白板", "闪退", "课件", "显卡"],
        "match": {"apps": ["希沃白板 5", "鸿合白板", "中庆白板", "天喻白板"]},
        "source": "通用经验",
    },
    {
        "id": "no-sound-hdmi",
        "category": "声音",
        "title": "一体机有画面但没声音",
        "symptom": "播放视频没有声音，音量条在动",
        "cause": "常见是音频输出设备被切到了 HDMI / 投影（声音跑到了投影仪那边），或音频服务未运行",
        "solution": "点右下角喇叭图标切换输出设备；仍在「维护 → 修复与清理」里执行「重启音频服务」",
        "tags": ["声音", "音频", "HDMI", "没声音"],
        "source": "通用经验",
    },
    {
        "id": "classroom-control-lock",
        "category": "课堂管理",
        "title": "鼠标键盘被锁、屏幕被控制",
        "symptom": "键鼠突然失灵，或屏幕被老师端操作",
        "cause": "教室管理软件（极域电子教室、联想/噢易集控等）正在广播或锁定学生端",
        "solution": "属正常教学行为；若是误锁，在教师端「停止广播/解锁」即可。排查时可先在任务管理器看看是否有课堂管理软件在运行",
        "tags": ["极域", "广播", "锁屏", "键鼠"],
        "match": {"apps": ["极域电子教室", "ClassIn"]},
        "source": "通用经验",
    },
    {
        "id": "disk-100-percent",
        "category": "性能",
        "title": "上课时整机卡顿、磁盘占用 100%",
        "symptom": "点什么都慢，任务管理器里磁盘长时间 100%",
        "cause": "机械硬盘老化、Windows 更新/索引后台跑、系统盘剩余空间过少都会导致",
        "solution": "在「维护」里清理临时文件并把 C 盘留出 15% 以上空间；机械硬盘的机器建议换 SSD；空闲时段再让系统完成更新",
        "tags": ["卡顿", "磁盘", "100%", "慢"],
        "source": "通用经验",
    },
    {
        "id": "usb-not-recognized",
        "category": "外设",
        "title": "U 盘插上不识别",
        "symptom": "插上 U 盘没反应，或提示「无法识别的 USB 设备」",
        "cause": "接口供电不足 / 前置接口线松、U 盘文件系统损坏、或被策略禁用了 USB 存储",
        "solution": "换到机身后置 USB 口试；在磁盘管理里看是否能看到盘（能看到说明是盘符/分区问题）；学校有 USB 策略的话需要管理员放行",
        "tags": ["U盘", "USB", "不识别"],
        "source": "通用经验",
    },
    {
        "id": "network-unstable",
        "category": "网络",
        "title": "网络时通时断 / 网页打不开",
        "symptom": "能连上但网页加载失败，或频繁掉线",
        "cause": "DNS 缓存异常、IP 地址冲突（同网段两台机器同 IP）、网线或交换机端口接触不良",
        "solution": "先用「维护 → 修复与清理」里的「清理 DNS 缓存」；再在「维护 → 诊断」里跑一遍分步诊断定位是哪一层断了；IP 冲突可把该机改成自动获取 IP",
        "tags": ["网络", "断网", "DNS", "掉线"],
        "source": "通用经验",
    },
    {
        "id": "slow-boot",
        "category": "性能",
        "title": "开机特别慢",
        "symptom": "按下电源到能用要好几分钟",
        "cause": "启动项过多、磁盘健康度下降、系统盘空间不足、还原软件开机扫描",
        "solution": "在「维护 → 诊断」里看启动项列表，禁用非必要项；用「硬件信息」页看硬盘健康度（低于 80% 建议尽快备份并换盘）；机械硬盘换 SSD 提升最明显",
        "tags": ["开机", "启动项", "慢"],
        "source": "通用经验",
    },
    {
        "id": "projector-flicker",
        "category": "投屏",
        "title": "投影画面闪烁 / 偶尔黑一下",
        "symptom": "投影画面间歇性闪烁、黑屏瞬间恢复",
        "cause": "线缆质量差或过长导致信号衰减、接口氧化、分辨率/刷新率超出投影仪支持范围",
        "solution": "换短一点、质量好的 HDMI 线；把刷新率降到 60Hz；清理接口氧化物，必要时换线槽里的延长线",
        "tags": ["投影", "闪烁", "黑屏", "HDMI"],
        "source": "通用经验",
    },
    {
        "id": "temp-too-high",
        "category": "硬件",
        "title": "一体机温度高、风扇声音大",
        "symptom": "机身发烫、风扇长时间高转速，偶发自动降频卡顿",
        "cause": "教室粉尘多，散热风道积灰是最主要原因；也可能 OPS 模块安装不到位",
        "solution": "断电后清理进风口与风扇积灰（每学期一次）；在「硬件信息」页记录温度基线，方便对比判断是否恶化",
        "tags": ["温度", "风扇", "积灰", "发烫"],
        "source": "通用经验",
    },
    {
        "id": "cssd-health-low",
        "category": "硬件",
        "title": "硬盘健康度下降（预警）",
        "symptom": "体检/硬件页显示硬盘健康度低于 80%，偶发卡顿或文件打不开",
        "cause": "机械硬盘出现坏道，或 SSD 写入寿命接近上限",
        "solution": "立即备份重要课件到 U 盘或其他机器；不要在这块盘上继续安装系统；联系维修更换硬盘后重装（换 SSD 顺带提速）",
        "tags": ["硬盘", "健康度", "坏道", "备份"],
        "source": "通用经验",
    },
]


# ══════════════════════════════════════════════════════════════
# 环境快照（用于匹配与问题上报）
# ══════════════════════════════════════════════════════════════

def environment() -> dict[str, Any]:
    """采集本机环境（全部为已有检测能力的结果，不重复造轮子）。"""
    try:
        from .classroom import report as classroom_report
    except ImportError:
        classroom_report = None  # type: ignore[assignment]

    try:
        from .hardware_detail import collect

        quick = collect(quick=True)
    except Exception:
        quick = {}

    os_name = f"{platform.system()} {platform.release()}"
    if platform.system() == "Windows":
        try:
            build = int(platform.version().split(".")[-1])
        except (ValueError, IndexError):
            build = 0
        os_name = "Windows 11" if build >= 22000 else "Windows 10" if build >= 10240 else "Windows"

    flags: dict[str, bool] = {}
    apps: list[str] = []
    if classroom_report is not None:
        try:
            result = classroom_report()
            for item in result.get("items", []):
                if item["key"] == "touch":
                    flags["touch"] = "未检测到触摸设备" not in item["detail"]
                elif item["key"] == "wireless":
                    flags["wireless"] = "支持无线投屏" in item["detail"]
                elif item["key"] == "restore":
                    flags["restoreGuard"] = "检测到还原" in item["detail"]
                elif item["key"] == "screen":
                    flags["multiMonitor"] = "仅 1 个显示设备" not in item["detail"]
            apps = [a["name"] for a in result.get("apps", [])]
        except Exception:
            pass

    return {
        "os": os_name,
        "osVersion": platform.version(),
        "hostname": platform.node(),
        "apps": apps,
        "flags": flags,
        "gpus": [g.get("name") for g in (quick.get("gpus") or []) if g.get("name")],
        "cpuTemp": quick.get("cpuTemp"),
        "capturedAt": round(time.time() * 1000),
    }


# ══════════════════════════════════════════════════════════════
# 本地累积（data/kb/local.json）
# ══════════════════════════════════════════════════════════════

def _local_path() -> Path:
    folder = config_dir() / "kb"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "local.json"


def _read_local() -> list[dict[str, Any]]:
    path = _local_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = data.get("entries") if isinstance(data, dict) else data
    return [e for e in (entries or []) if isinstance(e, dict) and e.get("title")]


def _write_local(entries: list[dict[str, Any]]) -> bool:
    try:
        _local_path().write_text(
            json.dumps({"version": _KB_VERSION, "entries": entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def all_entries() -> list[dict[str, Any]]:
    """内置条目 + 本地累积条目（本地条目标记 origin=local）。"""
    local = [{**e, "origin": "local", "source": e.get("source") or "本机累积"} for e in _read_local()]
    return [{**e, "origin": "builtin"} for e in _ENTRIES] + local


def stats() -> dict[str, Any]:
    local = _read_local()
    categories = sorted({e.get("category", "其他") for e in all_entries()})
    return {
        "version": _KB_VERSION,
        "builtin": len(_ENTRIES),
        "local": len(local),
        "total": len(_ENTRIES) + len(local),
        "categories": categories,
    }


# ══════════════════════════════════════════════════════════════
# 检索与匹配
# ══════════════════════════════════════════════════════════════

def search(keyword: str = "", category: str = "") -> list[dict[str, Any]]:
    """按关键词 / 分类检索（关键词匹配标题、症状、原因、方案与标签）。"""
    kw = (keyword or "").strip().lower()
    result: list[dict[str, Any]] = []
    for entry in all_entries():
        if category and entry.get("category") != category:
            continue
        if kw:
            blob = " ".join(
                str(entry.get(field, ""))
                for field in ("title", "symptom", "cause", "solution", "category")
            ) + " " + " ".join(entry.get("tags", []))
            if kw not in blob.lower():
                continue
        result.append(entry)
    return result


def match_environment() -> dict[str, Any]:
    """找出与这台机器相关的条目（依据系统版本、已装软件、能力标志）。"""
    env = environment()
    flags = env.get("flags", {})
    apps = env.get("apps", [])
    hits: list[dict[str, Any]] = []

    for entry in all_entries():
        rule = entry.get("match") or {}
        reasons: list[str] = []

        needed_flags = rule.get("flags") or []
        for flag in needed_flags:
            if flags.get(flag):
                reasons.append(
                    {
                        "touch": "本机支持触摸",
                        "wireless": "本机支持无线投屏",
                        "restoreGuard": "检测到还原保护软件",
                        "multiMonitor": "本机接了多个显示设备",
                    }.get(flag, flag)
                )

        needed_apps = rule.get("apps") or []
        for app in apps:
            if any(app == want or want in app for want in needed_apps):
                reasons.append(f"已安装「{app}」")

        if reasons:
            hits.append({**entry, "reasons": reasons})

    return {"environment": env, "items": hits, "total": len(hits)}


# ══════════════════════════════════════════════════════════════
# 累积与分享
# ══════════════════════════════════════════════════════════════

def add_entry(
    title: str,
    symptom: str,
    cause: str,
    solution: str,
    category: str = "其他",
    tags: str = "",
) -> dict[str, Any]:
    """把一条经验加进本地知识库（供以后所有机器复用/分享）。"""
    if not title.strip():
        return {"ok": False, "message": "标题不能为空"}
    entry = {
        "id": f"local-{int(time.time())}",
        "category": category or "其他",
        "title": title.strip(),
        "symptom": symptom.strip(),
        "cause": cause.strip(),
        "solution": solution.strip(),
        "tags": [t.strip() for t in tags.replace("，", ",").split(",") if t.strip()],
        "source": "本机记录",
        "addedAt": round(time.time() * 1000),
    }
    with _lock:
        entries = _read_local()
        entries.append(entry)
        if not _write_local(entries):
            return {"ok": False, "message": "写入失败（数据目录不可写）"}
    return {"ok": True, "message": "已加入本地知识库", "entry": entry}


def export_issue(description: str, category: str = "") -> dict[str, Any]:
    """导出标准化问题报告（含环境快照），可直接发给维护者或提 PR。"""
    import os

    env = environment()
    payload = {
        "kind": "openclass-box-issue",
        "version": 1,
        "createdAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "description": description,
        "environment": env,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    name = f"OpenClass-问题报告-{time.strftime('%Y%m%d-%H%M%S')}.json"

    folder = config_dir() / "kb" / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    local_file = folder / name
    try:
        local_file.write_text(text, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "message": f"写入失败：{exc}", "path": ""}

    saved_to = str(local_file)
    try:
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        if not desktop.is_dir():
            desktop = Path(os.path.expanduser("~"))
        target = desktop / name
        target.write_text(text, encoding="utf-8")
        saved_to = str(target)
    except OSError:
        pass

    return {
        "ok": True,
        "message": f"问题报告已导出：{saved_to}",
        "path": saved_to,
        "size": len(text.encode("utf-8")),
    }


def import_entries(payload: str) -> dict[str, Any]:
    """导入别处分享的条目（JSON 文本 / 文件路径），合并进本地知识库。"""
    text = payload
    maybe_path = Path(payload.strip().strip('"'))
    if len(payload) < 400 and maybe_path.exists() and maybe_path.suffix.lower() == ".json":
        try:
            text = maybe_path.read_text(encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "message": f"读取失败：{exc}"}

    try:
        data = json.loads(text)
    except ValueError:
        return {"ok": False, "message": "不是有效的 JSON"}

    incoming = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(incoming, list):
        return {"ok": False, "message": "格式不正确：需要一个条目数组"}

    valid = [e for e in incoming if isinstance(e, dict) and e.get("title")]
    if not valid:
        return {"ok": False, "message": "没有可导入的条目"}

    with _lock:
        existing = _read_local()
        have = {str(e.get("title")) for e in existing}
        added = 0
        for entry in valid:
            if str(entry.get("title")) in have:
                continue
            entry.setdefault("id", f"local-{int(time.time())}-{added}")
            entry.setdefault("source", "导入")
            existing.append(entry)
            added += 1
        if added and not _write_local(existing):
            return {"ok": False, "message": "写入失败（数据目录不可写）"}
    return {"ok": True, "message": f"已导入 {added} 条（跳过重复 {len(valid) - added} 条）"}
