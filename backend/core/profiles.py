"""
学期模式与配置模板 —— 把学校的时间节奏做进工具里。

学校场景有强周期性：开学、期中、期末、假期，每个节点要做的事不一样。
这里提供两件事：

  1. **学期模式检查**（开学 / 考试 / 假期）
     每套模式是一份检查清单，一键把该做的事跑一遍，结果可导出成报告
     （交给学校、维修人员或存档）。检查全部复用已有的实测能力，
     不新增任何「猜」的数据。

  2. **配置模板（.ocbprofile）**
     把一台「标准机」的偏好配置导出成文件，其他机器一键导入 ——
     同年级 / 同学科的机器配置保持一致，不用一台台点。
     只导出可移植的设置项（外观、关闭行为、安全监控、壁纸样式、机房参数），
     不含机器专属路径与文件。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .config import config

PROFILE_SUFFIX = ".ocbprofile"

# 可移植的配置键（前缀匹配，避免逐键维护）
_PORTABLE_PREFIXES = ("lan_", "wallpaper_")
_PORTABLE_KEYS = (
    "theme",
    "close_to_tray",
    "security_clipboard",
    "security_browser",
    "webconsole_port",
)

# 机器专属身份：虽然带 lan_ 前缀，但代表「这一台机器」，
# 导出到别的机器会顶掉对方的配对码 / 节点标识，必须排除
_MACHINE_LOCAL_KEYS = ("lan_pair_code", "lan_node_id", "lan_token", "lan_secret")


def _is_portable_key(key: str) -> bool:
    """该配置键是否适合跟着模板走（排除机器专属身份）。"""
    if key in _MACHINE_LOCAL_KEYS:
        return False
    return key in _PORTABLE_KEYS or key.startswith(_PORTABLE_PREFIXES)

MODES: list[dict[str, str]] = [
    {
        "id": "term_start",
        "name": "开学模式",
        "desc": "开学前把机器过一遍：软件、网络、投屏、触摸、声音、空间、还原状态",
    },
    {
        "id": "exam",
        "name": "考试模式",
        "desc": "考试前确认环境干净：管理软件、还原状态、后台占用、投影模式",
    },
    {
        "id": "holiday",
        "name": "假期模式",
        "desc": "放假前收尾：深度清理、硬件健康、生成报修清单",
    },
]


def _item(key: str, name: str, ok: bool, detail: str, suggest: str = "") -> dict[str, Any]:
    return {"key": key, "name": name, "ok": ok, "detail": detail, "suggest": suggest}


# ══════════════════════════════════════════════════════════════
# 单项检查（复用已有实测能力）
# ══════════════════════════════════════════════════════════════

def _check_clock() -> dict[str, Any]:
    """系统时间是否正常（时间错会导致证书、在线考试、更新全失效）。"""
    now = time.localtime()
    ok = 2024 <= now.tm_year <= 2100
    try:
        zone = time.tzname[0]
    except Exception:
        zone = "未知"
    detail = f"系统时间 {time.strftime('%Y-%m-%d %H:%M:%S')}（时区 {zone}）"
    return _item(
        "clock",
        "系统时间",
        ok,
        detail,
        "" if ok else "时间明显异常，请校正系统时间与时区，否则证书 / 在线考试 / 更新都会失败",
    )


def _check_teaching_apps(min_count: int = 1) -> dict[str, Any]:
    """教学软件是否就位。"""
    try:
        from .classroom import teaching_apps

        result = teaching_apps()
    except Exception as exc:
        return _item("apps", "教学软件", True, f"未能扫描教学软件：{exc}", "")
    apps = result.get("items") or []
    names = "、".join(f"{a['name']}" for a in apps[:5])
    ok = len(apps) >= min_count
    return _item(
        "apps",
        "教学软件",
        ok,
        f"识别到 {len(apps)} 个：{names}" if apps else "未识别到教学软件（希沃白板 / 鸿合 / 极域等）",
        "" if ok else "请确认白板与投屏软件是否已装齐；装了但没识别到可到「课堂」页重新扫描",
    )


def _check_restore_guard(expect_on: bool = False) -> dict[str, Any]:
    """还原保护状态。开学时通常希望开启（防止被改乱），考试前也需要。"""
    try:
        from .classroom import restore_guard

        result = restore_guard()
    except Exception as exc:
        return _item("restore", "还原环境", True, f"未能检测还原环境：{exc}", "")
    has_guard = "检测到还原" in result["detail"]
    ok = (has_guard == expect_on) if expect_on else True
    return _item(
        "restore",
        "还原环境",
        ok,
        result["detail"],
        "" if ok else "建议开启还原保护（冰点 / 慧盾等），避免学生改动影响下次上课",
    )


def _check_grades() -> dict[str, Any]:
    """硬盘健康度（有 SMART 数据时给出预警）。"""
    try:
        from .hardware_detail import collect

        data = collect(quick=True)
        disks = data.get("physicalDisks") or []
    except Exception as exc:
        return _item("disk-health", "硬盘健康", True, f"未能读取硬盘信息：{exc}", "")

    if not disks:
        return _item("disk-health", "硬盘健康", True, "未读取到物理硬盘信息（可能被驱动或权限限制）", "")

    worst: float | None = None
    worst_name = ""
    for disk in disks:
        health = disk.get("health")
        name = str(disk.get("model") or disk.get("name") or "硬盘")
        if isinstance(health, (int, float)):
            if worst is None or health < worst:
                worst = float(health)
                worst_name = name

    if worst is None:
        return _item("disk-health", "硬盘健康", True, f"共 {len(disks)} 块硬盘，本机未提供健康度数据", "")
    ok = worst >= 80
    return _item(
        "disk-health",
        "硬盘健康",
        ok,
        f"{worst_name} 健康度 {worst:.0f}%",
        "" if ok else "健康度偏低，请尽快备份重要课件并安排更换硬盘",
    )


def _check_background_load() -> dict[str, Any]:
    """后台占用（考试前关掉无关软件）。"""
    try:
        import psutil

        top = sorted(psutil.process_iter(["name", "memory_info"]), key=lambda p: -(
            p.info.get("memory_info").rss if p.info.get("memory_info") else 0
        ))[:1]
        mem = psutil.virtual_memory()
    except Exception as exc:
        return _item("load", "后台占用", True, f"未能读取进程信息：{exc}", "")

    heavy = ""
    if top:
        info = top[0].info
        heavy = f"，占用最高：{info.get('name')}（{info['memory_info'].rss / 1048576:.0f} MB）"
    ok = mem.percent < 85
    return _item(
        "load",
        "后台占用",
        ok,
        f"内存占用 {mem.percent:.0f}%{heavy}",
        "" if ok else "内存占用偏高，考试前建议关闭无关软件（浏览器多标签、视频播放器等）",
    )


def _check_cleanup_potential(min_mb: int = 300) -> dict[str, Any]:
    """假期：临时文件/缓存可清理的空间。"""
    try:
        from .cleanup import analyze

        result = analyze()
    except Exception as exc:
        return _item("cleanup", "可清理空间", True, f"未能分析磁盘占用：{exc}", "")
    items = result.get("items") or []
    total = sum(int(item.get("size") or 0) for item in items if item.get("exists"))
    mb = total / 1048576
    ok = mb < min_mb
    return _item(
        "cleanup",
        "可清理空间",
        True,
        f"当前可释放约 {mb:.0f} MB（临时文件 / 缓存）",
        f"建议在放假前执行一次清理（约 {mb:.0f} MB）" if mb >= min_mb else "",
    )


# ══════════════════════════════════════════════════════════════
# 学期模式
# ══════════════════════════════════════════════════════════════

def _base_items() -> list[dict[str, Any]]:
    """基础健康项（网络 / 声音 / 显示 / 磁盘 / 内存），直接复用体检结果。"""
    try:
        from .health import run_checks

        return list(run_checks().get("items") or [])
    except Exception:
        return []


def _mode_items(mode: str) -> list[dict[str, Any]]:
    items = _base_items()
    if mode == "term_start":
        items += [
            _check_teaching_apps(1),
            _check_restore_guard(expect_on=True),
            _check_clock(),
            _check_grades(),
        ]
    elif mode == "exam":
        items += [
            _check_restore_guard(expect_on=True),
            _check_background_load(),
            _check_clock(),
        ]
    elif mode == "holiday":
        items += [
            _check_cleanup_potential(),
            _check_grades(),
        ]
    return items


def run_mode(mode: str) -> dict[str, Any]:
    """执行一套学期模式检查。"""
    spec = next((m for m in MODES if m["id"] == mode), None)
    if spec is None:
        return {"ok": False, "message": f"未知模式：{mode}"}

    started = time.time()
    items = _mode_items(mode)
    ok_count = sum(1 for i in items if i["ok"])
    problems = [i for i in items if not i["ok"]]
    return {
        "ok": True,
        "mode": mode,
        "name": spec["name"],
        "desc": spec["desc"],
        "items": items,
        "okCount": ok_count,
        "total": len(items),
        "problems": [
            {"name": i["name"], "detail": i["detail"], "suggest": i["suggest"]} for i in problems
        ],
        "elapsedMs": round((time.time() - started) * 1000),
    }


def _report_text(result: dict[str, Any], hostname: str) -> str:
    lines = [
        f"OpenClass-Box {result['name']}检查报告",
        "=" * 40,
        f"主机：{hostname}",
        f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"结果：{result['okCount']}/{result['total']} 项通过",
        "",
        "各项明细",
        "-" * 40,
    ]
    for item in result["items"]:
        mark = "通过" if item["ok"] else "待处理"
        lines.append(f"[{mark}] {item['name']}：{item['detail']}")
        if not item["ok"] and item.get("suggest"):
            lines.append(f"        建议：{item['suggest']}")
    if result["problems"]:
        lines += ["", "需要处理", "-" * 40]
        for problem in result["problems"]:
            lines.append(f"· {problem['name']}：{problem['detail']}")
            if problem.get("suggest"):
                lines.append(f"  建议：{problem['suggest']}")
    return "\n".join(lines)


def export_report(mode: str) -> dict[str, Any]:
    """跑一遍模式检查并导出报告到桌面。"""
    import os
    import platform

    result = run_mode(mode)
    if not result.get("ok"):
        return {"ok": False, "message": result.get("message", "检查失败"), "path": ""}

    text = _report_text(result, platform.node())
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = f"OpenClass-{result['name']}报告-{stamp}.txt"

    folder = Path(os.path.expanduser("~")) / "Desktop"
    if not folder.is_dir():
        folder = Path(os.path.expanduser("~"))
    target = folder / name
    try:
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "message": f"写入失败：{exc}", "path": ""}

    return {
        "ok": True,
        "message": f"{result['name']}报告已导出：{target}",
        "path": str(target),
        "summary": f"{result['okCount']}/{result['total']} 项通过",
        "path_for_api": "",
    }


# ══════════════════════════════════════════════════════════════
# 配置模板
# ══════════════════════════════════════════════════════════════

def _portable_settings() -> dict[str, Any]:
    snapshot = config.snapshot()
    portable: dict[str, Any] = {}
    for key, value in snapshot.items():
        if _is_portable_key(key):
            portable[key] = value
    return portable


def export_profile(note: str = "") -> dict[str, Any]:
    """把当前设置导出成 .ocbprofile（放桌面）。"""
    import os
    import platform

    payload = {
        "kind": "openclass-box-profile",
        "version": 1,
        "note": note,
        "createdAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hostname": platform.node(),
        "settings": _portable_settings(),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    name = f"OpenClass-配置模板-{time.strftime('%Y%m%d-%H%M%S')}{PROFILE_SUFFIX}"

    folder = Path(os.path.expanduser("~")) / "Desktop"
    if not folder.is_dir():
        folder = Path(os.path.expanduser("~"))
    target = folder / name
    try:
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "message": f"导出失败：{exc}", "path": ""}

    count = len(payload["settings"])
    return {
        "ok": True,
        "message": f"已导出 {count} 项设置到 {target}",
        "path": str(target),
        "count": count,
    }


def import_profile(path: str) -> dict[str, Any]:
    """导入 .ocbprofile 并应用（返回哪些设置被改了）。"""
    target = Path((path or "").strip().strip('"'))
    if not target.exists() or not target.is_file():
        return {"ok": False, "message": "文件不存在"}

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"ok": False, "message": f"读取失败：{exc}"}

    if not isinstance(data, dict) or data.get("kind") != "openclass-box-profile":
        return {"ok": False, "message": "不是有效的配置模板文件（.ocbprofile）"}

    settings = data.get("settings")
    if not isinstance(settings, dict) or not settings:
        return {"ok": False, "message": "模板里没有可应用的设置"}

    applied: list[str] = []
    failed: list[str] = []
    for key, value in settings.items():
        if not _is_portable_key(key):
            continue
        if config.set(key, value):
            applied.append(key)
        else:
            failed.append(key)

    message = f"已应用 {len(applied)} 项设置"
    if failed:
        message += f"；{len(failed)} 项写入失败（数据目录不可写）"
    return {
        "ok": bool(applied),
        "message": message,
        "applied": applied,
        "failed": failed,
        "from": str(target),
    }
