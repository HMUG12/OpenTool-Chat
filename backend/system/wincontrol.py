"""
窗口控制 —— 直接用 Win32 API 操作主窗口。

为什么不用 pywebview 自带的 maximize/minimize：
  pywebview 的 maximized 状态依赖后端事件回传，frameless 窗口在
  「最大化 → 最小化 → 再恢复」这条路径上状态会不同步，表现为最小化后
  点最大化按钮没反应、无法再次全屏。
  这里改为对同一窗口句柄直接调用 IsZoomed / ShowWindow，
  行为与系统原生窗口按钮完全一致。
"""
from __future__ import annotations

import ctypes
import platform

SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9
GW_OWNER = 4

_TITLE = "OpenClass-Box"


def _user32():
    return ctypes.windll.user32


def _hwnd() -> int:
    """定位主窗口句柄：先按标题找，找不到再按进程枚举顶层窗口。"""
    if platform.system() != "Windows":
        return 0
    try:
        user32 = _user32()
        handle = user32.FindWindowW(None, _TITLE)
        if handle:
            return int(handle)

        pid = int(ctypes.windll.kernel32.GetCurrentProcessId())
        found: list[int] = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _enum(hwnd, _lparam):  # type: ignore[no-untyped-def]
            owner_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
            if (
                owner_pid.value == pid
                and user32.IsWindowVisible(hwnd)
                and user32.GetWindow(hwnd, GW_OWNER) == 0
            ):
                found.append(int(hwnd))
                return False  # 找到即停
            return True

        user32.EnumWindows(_enum, 0)
        return found[0] if found else 0
    except (AttributeError, OSError):
        return 0


def minimize() -> bool:
    handle = _hwnd()
    if not handle:
        return False
    return bool(_user32().ShowWindow(handle, SW_MINIMIZE))


def toggle_maximize() -> bool:
    """在最大化 / 还原之间切换。

    关键修复：「最大化 → 最小化 → 再点最大化」这条路径上，窗口被最小化时
    IsZoomed 仍为真，直接走 restore 只会把它还原成普通窗口，表现为
    「最小化之后再也回不到全屏」。这里按真实状态分三种情况处理：
      - 已最小化：先还原；若还原后不是最大化再最大化；
      - 已最大化：还原为窗口；
      - 普通窗口：最大化。
    """
    handle = _hwnd()
    if not handle:
        return False
    user32 = _user32()
    if user32.IsIconic(handle):
        user32.ShowWindow(handle, SW_RESTORE)
        if not user32.IsZoomed(handle):
            user32.ShowWindow(handle, SW_MAXIMIZE)
        return True
    if user32.IsZoomed(handle):
        user32.ShowWindow(handle, SW_RESTORE)
    else:
        user32.ShowWindow(handle, SW_MAXIMIZE)
    return True


def is_maximized() -> bool:
    handle = _hwnd()
    if not handle:
        return False
    return bool(_user32().IsZoomed(handle))


def restore() -> bool:
    """把处于最小化状态的窗口还原（供托盘图标点击时使用）。

    注意 SW_RESTORE 会同时把「最大化但被最小化」的窗口还原为最大化状态，
    行为与点击任务栏按钮一致。
    """
    handle = _hwnd()
    if not handle:
        return False
    user32 = _user32()
    if user32.IsIconic(handle):
        user32.ShowWindow(handle, SW_RESTORE)
    return True
