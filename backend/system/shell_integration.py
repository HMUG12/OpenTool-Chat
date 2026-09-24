"""
右键「打开方式」注册 —— 把 OpenClass 收编进文件右键菜单。

仅在已打包为 OpenClass.exe 后生效（开发态 Python 没有 exe 名可注册）。
写入当前用户注册表（HKCU），无需管理员权限。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

try:
    import winreg
except ImportError:
    winreg = None

from ..core.app_locator import FILE_ROUTES

APP_EXE_NAME = "OpenClass-Box.exe"
_APPS_KEY = rf"Software\Classes\Applications\{APP_EXE_NAME}"


def _exe_path() -> Path | None:
    if getattr(sys, "frozen", False) and Path(sys.executable).name.lower() == APP_EXE_NAME.lower():
        return Path(sys.executable)
    return None


def _supported_types() -> List[str]:
    seen: List[str] = []
    for ext in FILE_ROUTES:
        if ext not in seen:
            seen.append(ext)
    return seen


def _delete_tree(key) -> None:
    """递归删除一个已打开注册表键下的所有子项（不删自身）。"""
    try:
        while True:
            sub = winreg.EnumKey(key, 0)
            with winreg.OpenKey(key, sub, 0, winreg.KEY_ALL_ACCESS) as subkey:
                _delete_tree(subkey)
            winreg.DeleteKey(key, sub)
    except OSError:
        pass


def _remove_key(parent_hkey, sub: str) -> None:
    try:
        with winreg.OpenKey(parent_hkey, sub, 0, winreg.KEY_ALL_ACCESS) as key:
            _delete_tree(key)
        winreg.DeleteKey(parent_hkey, sub)
    except OSError:
        pass


def set_openwith(enabled: bool) -> bool:
    if not winreg:
        return False
    exe = _exe_path()
    if exe is None:
        return False
    try:
        if enabled:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _APPS_KEY)
            winreg.SetValueEx(key, "FriendlyAppName", 0, winreg.REG_SZ, "OpenClass 集成套件")
            cmd_key = winreg.CreateKey(key, r"shell\open\command")
            winreg.SetValueEx(cmd_key, None, 0, winreg.REG_SZ, f'"{exe}" "%1"')
            winreg.CloseKey(cmd_key)
            types_key = winreg.CreateKey(key, "SupportedTypes")
            for ext in _supported_types():
                winreg.SetValueEx(types_key, ext, 0, winreg.REG_SZ, "")
            winreg.CloseKey(types_key)
            winreg.CloseKey(key)

            # 让具体扩展名的右键「打开方式」直接列出 OpenClass
            for ext in _supported_types():
                ol_key = winreg.CreateKey(
                    winreg.HKEY_CURRENT_USER,
                    rf"Software\Classes\{ext}\OpenWithList\{APP_EXE_NAME}",
                )
                winreg.CloseKey(ol_key)
        else:
            _remove_key(winreg.HKEY_CURRENT_USER, _APPS_KEY)
            for ext in _supported_types():
                try:
                    ext_key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        rf"Software\Classes\{ext}\OpenWithList",
                        0,
                        winreg.KEY_ALL_ACCESS,
                    )
                    _remove_key(ext_key, APP_EXE_NAME)
                    winreg.CloseKey(ext_key)
                except OSError:
                    pass
        return True
    except OSError:
        return False


def is_openwith() -> bool:
    """是否已注册「打开方式」入口。"""
    if not winreg:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _APPS_KEY)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def ensure_openwith() -> None:
    """注册表路径自愈：若已注册但记录的 exe 路径与当前不一致（如整体移动了
    文件夹），自动用当前路径重写，实现「移动后无需手动重注册」的便携性。"""
    if not winreg or _exe_path() is None:
        return
    if not is_openwith():
        return
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, rf"{_APPS_KEY}\shell\open\command"
        ) as key:
            current, _ = winreg.QueryValueEx(key, None)
    except OSError:
        set_openwith(True)
        return
    import re

    m = re.match(r'"([^"]+)"', current)
    registered_exe = m.group(1) if m else (current.split()[0] if current.split() else "")
    if registered_exe:
        try:
            if Path(registered_exe).resolve() != _exe_path().resolve():
                set_openwith(True)
        except OSError:
            pass
