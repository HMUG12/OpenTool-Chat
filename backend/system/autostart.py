"""
开机自启 —— 写入/移除当前用户的注册表 Run 键。

仅作用于当前用户（HKEY_CURRENT_USER），不需要管理员权限，
也不会污染全局。打包成 exe 后写入的是 exe 路径；开发态写入 python main.py。
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "OpenClass-Box"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --hidden'
    root = Path(__file__).resolve().parents[2]
    py = sys.executable
    main = root / "main.py"
    return f'"{py}" "{main}" --hidden'


def set_autostart(enabled: bool) -> bool:
    if not winreg:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except OSError:
                pass
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def is_autostart() -> bool:
    if not winreg:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False
