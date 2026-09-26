"""
一键清理 —— 统计并清理常见垃圾文件。

原则：
  - 只清理**系统公认的缓存/临时位置**，绝不碰用户的文档、下载等个人文件；
  - 每个位置先统计真实占用，清理后回报真实释放量；
  - 被占用的文件自动跳过（正在运行的软件不会被破坏）。
"""
from __future__ import annotations

import ctypes
import os
import shutil
from pathlib import Path
from typing import Any


def _dir_size(path: Path) -> int:
    """统计目录占用（失败即跳过）。"""
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    continue
    except OSError:
        pass
    return total


def _locations() -> list[dict[str, Any]]:
    """可清理位置（全部为系统缓存/临时目录）。"""
    home = Path(os.path.expanduser("~"))
    return [
        {
            "key": "temp",
            "name": "用户临时文件",
            "path": Path(os.environ.get("TEMP", "")),
            "desc": "程序运行产生的临时文件，可安全清理",
        },
        {
            "key": "thumb",
            "name": "缩略图缓存",
            "path": home / "AppData" / "Local" / "Microsoft" / "Windows" / "Explorer",
            "desc": "资源管理器的缩略图数据库，清理后会自动重建",
        },
        {
            "key": "edge_cache",
            "name": "Edge 浏览器缓存",
            "path": home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
            "desc": "网页缓存；Edge 正在运行时可能跳过部分文件",
        },
        {
            "key": "recycle",
            "name": "回收站",
            "path": None,
            "desc": "已删除文件的暂存区，清空后无法恢复",
        },
    ]


def analyze() -> dict[str, Any]:
    """统计各清理项的真实占用。"""
    items: list[dict[str, Any]] = []
    total = 0
    for loc in _locations():
        path = loc["path"]
        if path is None:  # 回收站：用系统 API 统计
            size = _recycle_size()
            items.append({**loc, "path": "回收站", "size": size, "exists": size > 0})
        else:
            exists = bool(path) and path.is_dir()
            size = _dir_size(path) if exists else 0
            items.append({**loc, "path": str(path), "size": size, "exists": exists})
        total += items[-1]["size"]
    return {"items": items, "total": total}


def _recycle_size() -> int:
    """通过 Shell API 查询回收站占用（查不到返回 0）。"""
    try:
        class _SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_ulong), ("i64Size", ctypes.c_longlong),
                        ("i64NumItems", ctypes.c_longlong)]

        info = _SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(info)
        rc = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        return int(info.i64Size) if rc == 0 else 0
    except (AttributeError, OSError):
        return 0


def _empty_recycle() -> bool:
    """清空回收站（静默）。"""
    try:
        # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        rc = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
        return rc == 0
    except (AttributeError, OSError):
        return False


def _remove_children(path: Path) -> int:
    """删除目录内的所有内容，返回成功删除的条目数（占用中的自动跳过）。"""
    removed = 0
    try:
        for item in path.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink()
                removed += 1
            except OSError:
                continue
    except OSError:
        pass
    return removed


def run(keys: list[str]) -> dict[str, Any]:
    """执行清理，返回真实释放量。"""
    before = {item["key"]: item["size"] for item in analyze()["items"]}
    details: list[str] = []

    for loc in _locations():
        if loc["key"] not in keys:
            continue

        if loc["key"] == "recycle":
            ok = _empty_recycle()
            details.append(f"{loc['name']}：{'已清空' if ok else '清空失败'}")
            continue

        path = loc["path"]
        if not path or not path.is_dir():
            details.append(f"{loc['name']}：目录不存在，已跳过")
            continue

        count = _remove_children(path)
        details.append(f"{loc['name']}：已清理 {count} 项")

    after = {item["key"]: item["size"] for item in analyze()["items"]}
    freed = sum(max(0, before.get(k, 0) - after.get(k, 0)) for k in keys)

    return {"ok": True, "freed": freed, "details": details}
