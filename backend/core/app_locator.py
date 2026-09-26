"""
定位本机已安装的第三方应用，并把文件扩展名路由到对应工具。

设计立场（图吧式工具箱）：**不内置** 7-Zip / VLC / LibreOffice / OpenOffice
这些数百 MB 级的大型软件，而是「发现并调度」本机已安装的版本，或 tools/
目录下的便携版。找不到时相关工具标记为不可用，而非报错。

这样 OpenClass 本身保持轻量（几 MB），又能把专业软件统一收编进右键菜单。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .paths import app_root

try:
    import winreg
except ImportError:  # 非 Windows（仅用于开发预览）
    winreg = None


# 每个应用的定位策略，按顺序尝试：App Paths 注册表 → 软件注册表 → 常见目录 → 便携版
_APPS: dict[str, dict] = {
    "7zip": {
        "app_paths": "7zFM.exe",
        "reg_keys": (
            [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\7-Zip", ("Path64", "Path32"), "7zFM.exe")]
            if winreg else []
        ),
        "program_dirs": ["7-Zip\\7zFM.exe"],
        "portable": ("7zip", ("7zFM.exe", "7zG.exe")),
    },
    "vlc": {
        "app_paths": "vlc.exe",
        "reg_keys": [],
        "program_dirs": ["VideoLAN\\VLC\\vlc.exe"],
        "portable": ("vlc", ("vlc.exe",)),
    },
    "libreoffice": {
        "app_paths": "soffice.exe",
        # 与 OpenOffice 同名，必须用目录关键字区分，否则会误指向 OpenOffice
        "app_paths_hint": "libreoffice",
        "reg_keys": (
            [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\LibreOffice\LibreOffice", ("Path",), "program\\soffice.exe")]
            if winreg else []
        ),
        "program_dirs": ["LibreOffice\\program\\soffice.exe"],
        "portable": ("libreoffice", ("program\\soffice.exe",)),
    },
    "openoffice": {
        "app_paths": "soffice.exe",
        "app_paths_hint": "openoffice",
        "reg_keys": [],
        # OpenOffice 4.1.x 无法在非 ASCII（中文）路径下运行，会报
        # "central configuration" 错误。因此除 tools/ 便携版外，额外支持
        # 放到纯 ASCII 目录的完整副本，并优先于中文路径下的便携版。
        "abs_paths": [
            "D:\\OpenClassOO\\program\\soffice.exe",
            "C:\\OpenClassOO\\program\\soffice.exe",
            "C:\\Program Files\\OpenOffice 4\\program\\soffice.exe",
            "C:\\Program Files (x86)\\OpenOffice 4\\program\\soffice.exe",
            "D:\\Program Files\\OpenOffice 4\\program\\soffice.exe",
            "C:\\Program Files\\OpenOffice.org 3\\program\\soffice.exe",
        ],
        "program_dirs": [
            "OpenOffice 4\\program\\soffice.exe",
            "OpenOffice\\program\\soffice.exe",
        ],
        "portable": ("openoffice", ("program\\soffice.exe",)),
    },
}

# 应用名 → 工具 id（与 tools/<name>/tool.json 的 id 对应）
_APP_TO_TOOL: dict[str, str] = {
    "7zip": "seven_zip",
    "vlc": "vlc",
    "libreoffice": "libreoffice",
    "openoffice": "openoffice",
}

# 扩展名 → 应用名（用于右键「打开方式」/双击路由）
FILE_ROUTES: dict[str, str] = {
    ".zip": "7zip", ".7z": "7zip", ".rar": "7zip", ".tar": "7zip",
    ".gz": "7zip", ".bz2": "7zip", ".xz": "7zip", ".iso": "7zip", ".001": "7zip",
    ".mp4": "vlc", ".mkv": "vlc", ".avi": "vlc", ".mov": "vlc", ".flv": "vlc",
    ".wmv": "vlc", ".mpg": "vlc", ".mpeg": "vlc", ".webm": "vlc",
    ".mp3": "vlc", ".flac": "vlc", ".wav": "vlc", ".m4a": "vlc",
    ".aac": "vlc", ".ogg": "vlc", ".wma": "vlc", ".ape": "vlc",
    ".doc": "libreoffice", ".docx": "libreoffice", ".xls": "libreoffice",
    ".xlsx": "libreoffice", ".ppt": "libreoffice", ".pptx": "libreoffice",
    ".odt": "libreoffice", ".ods": "libreoffice", ".odp": "libreoffice",
    ".rtf": "libreoffice", ".csv": "libreoffice", ".pdf": "libreoffice",
}


def _from_app_paths(exe_name: str, hint: str = "") -> Optional[Path]:
    """从 App Paths 注册表定位。

    hint 是路径必须包含的关键字（小写）：OpenOffice 与 LibreOffice 的
    可执行文件同名（都是 soffice.exe），只按文件名匹配会把两者搞混，
    必须用目录关键字区分。
    """
    if not winreg or not exe_name:
        return None
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
        )
        value, _ = winreg.QueryValueEx(key, None)
        path = Path(value)
        if path.exists() and (not hint or hint in str(path).lower()):
            return path
    except OSError:
        pass
    return None


def _from_reg_keys(specs: list) -> Optional[Path]:
    if not winreg:
        return None
    for hkey, sub, valnames, suffix in specs:
        try:
            key = winreg.OpenKey(hkey, sub)
        except OSError:
            continue
        try:
            for v in valnames:
                try:
                    base, _ = winreg.QueryValueEx(key, v)
                except OSError:
                    continue
                path = Path(base) / suffix
                if path.exists():
                    return path
        finally:
            winreg.CloseKey(key)
    return None


def _from_program_dirs(rel_names: list[str]) -> Optional[Path]:
    bases = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        "C:\\Program Files",
        "C:\\Program Files (x86)",
    ]
    for base in bases:
        if not base:
            continue
        for rel in rel_names:
            path = Path(base) / rel
            if path.exists():
                return path
    return None


def _from_abs_paths(paths: list[str]) -> Optional[Path]:
    """按绝对路径直接查找。

    用于无法放在中文路径下运行的软件（如 OpenOffice 4.1.x），
    允许把它们放到纯 ASCII 目录后再被发现。
    """
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            return path
    return None


def _from_portable(subdir: str, names: tuple[str, ...]) -> Optional[Path]:
    root = app_root()  # 全局路径真相：开发态为项目根，打包态为 exe 目录
    folder = root / "tools" / subdir
    if not folder.is_dir():
        return None
    # 递归查找，容忍不同便携版解压出的目录层级（如 vlc-3.0.21\vlc.exe）
    for name in names:
        for hit in folder.rglob(name):
            if hit.is_file():
                return hit
    return None


def find_app(name: str) -> Optional[Path]:
    """返回应用可执行文件路径；找不到返回 None。"""
    spec = _APPS.get(name)
    if not spec:
        return None
    for finder in (
        lambda: _from_abs_paths(spec.get("abs_paths", [])),
        lambda: _from_app_paths(spec.get("app_paths", ""), spec.get("app_paths_hint", "")),
        lambda: _from_reg_keys(spec.get("reg_keys", [])),
        lambda: _from_program_dirs(spec.get("program_dirs", [])),
        lambda: _from_portable(*spec.get("portable", ("", ()))),
    ):
        path = finder()
        if path:
            return path
    return None


def route_file(path: str | os.PathLike) -> Optional[str]:
    """根据文件扩展名返回应使用的工具 id；无匹配返回 None。"""
    suffix = Path(path).suffix.lower()
    app = FILE_ROUTES.get(suffix)
    if not app:
        return None
    return _APP_TO_TOOL.get(app)
