"""
暴露给前端的 API —— pywebview 会把本类的方法挂载到 window.pywebview.api，
前端以 Promise 形式调用（见 frontend/src/api.ts 的 OcApi 接口定义）。
"""
from __future__ import annotations

import platform

import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

from . import __version__
from .core import paths
from .core.config import config
from .core.monitor import monitor, query_public_ip
from .core.registry import tool_registry as registry
from .core.runner import launch_detached, open_in_explorer

AUTHOR = "OpenClass Contributors"
DESCRIPTION = "开源实用工具箱"

# 合法的展示名 ↔ 内部值
_VALID_THEMES = ("light", "dark", "system")


class Api:
    """前端 ⇄ Python 的边界。所有方法返回值必须是 JSON 可序列化对象。"""

    def __init__(self) -> None:
        self._window: Any = None
        self.tray_available: bool = False
        registry.scan()
        monitor.start()

    # pywebview 窗口创建后回调注入，用于窗口控制
    def attach_window(self, window: Any) -> None:
        self._window = window

    # ══════════════════════════════════════════════════════
    # 元信息
    # ══════════════════════════════════════════════════════

    def get_info(self) -> dict[str, Any]:
        return {
            "name": "OpenClass-Box",
            "version": __version__,
            "author": AUTHOR,
            "description": DESCRIPTION,
            "portable": True,
            "rootDir": str(paths.app_root()),
            "toolDir": str(paths.tools_dir()),
            "pythonVersion": platform.python_version(),
            "platform": platform.system(),
        }

    # ══════════════════════════════════════════════════════
    # 工具管理
    # ══════════════════════════════════════════════════════

    def list_tools(self) -> list[dict[str, Any]]:
        if registry.count() == 0:
            registry.scan()
        return [t.to_dict() for t in registry.list()]

    def refresh_tools(self) -> int:
        registry.scan()
        return registry.count()

    def check_updates(self, force: bool = False) -> list[dict[str, Any]]:
        """检查各集成组件是否有新版本（联网查询，断网返回空列表）。"""
        from .core.updater import check_updates

        return check_updates(force=force)

    def check_url(self, url: str) -> dict[str, Any]:
        """对网址做安全评分，返回 score / level(safe|warn|danger) / reasons。"""
        from .core.url_guard import check_url

        return check_url(url)

    def url_alerts(self) -> list[dict[str, Any]]:
        """取出剪贴板监听产生的风险网址告警（取出即清空）。"""
        from .core.url_watch import alerts

        return alerts()

    def search_music(self, keyword: str = "") -> list[dict[str, Any]]:
        """搜索本地音乐库（空关键词返回全部，最多 200 条）。"""
        from .core.music import search

        return search(keyword)

    def music_url(self, path: str) -> str:
        """把本地音频路径转成前端可直接播放的 URL。"""
        from .core.music import media_url

        return media_url(path)

    def search_music_online(self, keyword: str, platform: str = "netease") -> list[dict[str, Any]]:
        """在线搜索音频（当前支持网易云）。"""
        from .core.music import search_online

        return search_online(keyword, platform)

    def fetch_music(self, song_id: str, platform: str = "netease") -> str:
        """把在线音频拉取到本地，返回本地路径（失败返回空串）。"""
        from .core.music import fetch_online

        return fetch_online(song_id, platform)

    def list_wallpapers(self, directory: str = "") -> list[dict[str, Any]]:
        """列出可用作壁纸的图片。"""
        from .core.wallpaper import list_images

        return list_images(directory)

    def set_wallpaper(self, path: str) -> bool:
        """把指定图片设为桌面壁纸。"""
        from .core.wallpaper import set_wallpaper

        return set_wallpaper(path)

    def random_wallpaper(self, directory: str = "") -> dict[str, Any]:
        """从目录随机更换壁纸。"""
        from .core.wallpaper import random_wallpaper

        return random_wallpaper(directory)

    def run_health_checks(self) -> dict[str, Any]:
        """一键体检：网络 / 声音 / 显示 / 磁盘 / 内存（全部离线）。"""
        from .core.health import run_checks

        return run_checks()

    def list_repairs(self) -> list[dict[str, Any]]:
        """列出可用的修复动作。"""
        from .core.repair import list_repairs

        return list_repairs()

    def run_repair(self, key: str) -> dict[str, Any]:
        """执行一个修复动作（需要管理员的会弹 UAC 确认）。"""
        from .core.repair import run_repair

        return run_repair(key)

    def export_report(self) -> dict[str, Any]:
        """导出报修信息报告到桌面，返回 {ok, path, content}。"""
        from .core.report import export

        return export()

    def analyze_cleanup(self) -> dict[str, Any]:
        """统计可清理项及真实占用。"""
        from .core.cleanup import analyze

        return analyze()

    def run_cleanup(self, keys: list[str]) -> dict[str, Any]:
        """执行清理，返回真实释放量。"""
        from .core.cleanup import run

        return run(keys)

    def run_netdiag(self) -> dict[str, Any]:
        """网络分步诊断（本机 / 网关 / DNS / 外网）。"""
        from .core.netdiag import run_diagnostics

        return run_diagnostics()

    def list_packages(self, directory: str = "") -> dict[str, Any]:
        """列出离线软件目录里的安装包。"""
        from .core.software import list_packages

        return list_packages(directory)

    def install_package(self, path: str) -> dict[str, Any]:
        """启动一个安装包（交给系统安装向导）。"""
        from .core.software import install

        return install(path)

    def list_restore_points(self) -> dict[str, Any]:
        """列出系统还原点（只读）。"""
        from .core.restore import list_points

        return list_points()

    def create_restore_point(self, description: str = "") -> dict[str, Any]:
        """创建系统还原点（需要管理员确认）。"""
        from .core.restore import create_point

        return create_point(description)

    def export_diagnostics(self) -> dict[str, Any]:
        """生成诊断包（系统信息 + 体检 + 事件日志）到桌面。"""
        from .core.logs import export

        return export()

    def list_processes(self, limit: int = 40) -> dict[str, Any]:
        """按内存占用列出进程。"""
        from .core.procs import list_processes

        return list_processes(limit)

    def kill_process(self, pid: int) -> dict[str, Any]:
        """结束指定进程（系统关键进程会被拒绝）。"""
        from .core.procs import kill_process

        return kill_process(pid)

    def list_services(self, limit: int = 150) -> dict[str, Any]:
        """列出 Windows 服务。"""
        from .core.procs import list_services

        return list_services(limit)

    def list_startup(self) -> dict[str, Any]:
        """列出开机启动项。"""
        from .core.procs import list_startup

        return list_startup()

    def launch_tool(self, tool_id: str, file_path: str | None = None) -> dict[str, Any]:
        spec = registry.get(tool_id)
        if spec is None:
            return {"ok": False, "message": f"未找到工具：{tool_id}"}

        entry = spec.entry_path
        # 应用桥接类工具：每次启动都重新定位，支持使用期间安装/放置便携版
        if spec.app:
            from .core.app_locator import find_app

            exe = find_app(spec.app)
            if exe:
                entry = exe
                spec.available = True
            else:
                spec.available = False
                spec.reason = f"未检测到 {spec.app}，请安装后重试或在设置中指定路径"

        if not spec.available:
            return {"ok": False, "message": spec.reason or "工具当前不可用"}

        args = list(spec.args)
        if file_path:
            if any("{file}" in a for a in args):
                args = [a.replace("{file}", file_path) for a in args]
            else:
                args.append(file_path)

        ok, message = launch_detached(entry, args, spec.admin)
        if ok:
            return {"ok": True, "message": f"已启动「{spec.name}」"}
        return {"ok": False, "message": message}

    def open_file_with(self, path: str) -> dict[str, Any]:
        """按扩展名路由到集成工具并打开该文件（右键「打开方式」后端）。"""
        from .core.app_locator import route_file

        tool_id = route_file(path)
        if not tool_id:
            return {"ok": False, "message": f"暂不支持以集成套件打开该类型：{Path(path).suffix}"}
        return self.launch_tool(tool_id, path)

    def reveal_tool(self, tool_id: str) -> bool:
        """在资源管理器中定位工具所在位置。"""
        spec = registry.get(tool_id)
        if spec is None:
            return False

        target = spec.entry_path
        if target.is_file():
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", "/select,", str(target)])
                return True
            ok, _ = open_in_explorer(target.parent)
            return ok

        target_dir = target if target.is_dir() else target.parent
        ok, _ = open_in_explorer(target_dir)
        return ok

    # ══════════════════════════════════════════════════════
    # 系统监测（主页数据源）
    # ══════════════════════════════════════════════════════

    def get_hardware(self) -> dict[str, Any]:
        """静态硬件信息。首次调用较慢（含 WMI 查询），之后走缓存。"""
        return monitor.hardware()

    def get_metrics(self) -> dict[str, Any]:
        """实时指标快照，含最近 60 秒的采样历史。"""
        return monitor.metrics()

    def get_network(self) -> dict[str, Any]:
        """网卡列表与网络拓扑（网关 / DNS）。"""
        return monitor.network()

    def get_ip(self) -> dict[str, Any]:
        """本机 IP 信息。不含公网查询，以保证离线环境下的响应速度。"""
        return monitor.ip(include_public=False)

    def query_public_ip(self) -> dict[str, Any]:
        """联网查询公网出口 IP。离线时返回 reachable=False。"""
        return query_public_ip()

    # ══════════════════════════════════════════════════════
    # 偏好与系统交互
    # ══════════════════════════════════════════════════════

    def get_theme(self) -> str:
        value = config.get("theme", "system")
        return value if value in _VALID_THEMES else "system"

    def set_theme(self, mode: str) -> bool:
        if mode not in _VALID_THEMES:
            return False
        config.set("theme", mode)
        return True

    def open_url(self, url: str) -> bool:
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False

    def open_tool_dir(self) -> bool:
        ok, _ = open_in_explorer(paths.tools_dir())
        return ok

    # ══════════════════════════════════════════════════════
    # 窗口控制（frameless 自绘标题栏）
    # ══════════════════════════════════════════════════════

    def window_minimize(self) -> None:
        if self._window is not None:
            self._window.minimize()

    def window_toggle_maximize(self) -> None:
        if self._window is None:
            return
        try:
            if self._window.maximized:
                self._window.restore()
            else:
                self._window.maximize()
        except Exception:
            pass

    def window_close(self) -> None:
        """关闭按钮 = 最小化到托盘（常驻后台）；无托盘时才是真正退出。"""
        if self._window is None:
            return
        if self.tray_available:
            self._window.hide()
        else:
            self._window.destroy()

    def window_start_drag(self) -> None:
        """标题栏拖动：交给 pywebview 内置方法。

        当 main.py 中 create_window(easy_drag=True) 时，拖动已由 Win32 层在
        frameless 下自动接管，此方法通常不再被调用（保留以防前端仍触发）。
        """
        if self._window is not None:
            try:
                self._window.start_drag()
            except Exception:
                pass

    def open_url(self, url: str) -> None:
        """未检测到外部应用时，打开官方下载页。"""
        import webbrowser

        try:
            webbrowser.open(str(url))
        except Exception:
            pass

    def window_quit(self) -> None:
        """真正退出（托盘菜单「退出」调用）。"""
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                import os

                os._exit(0)


    def get_autostart(self) -> bool:
        from .system.autostart import is_autostart

        return is_autostart()

    def set_autostart(self, enabled: bool) -> bool:
        from .system.autostart import set_autostart

        ok = set_autostart(bool(enabled))
        if ok:
            config.set("autostart", bool(enabled))
        return ok

    def set_openwith_registered(self, enabled: bool) -> bool:
        """注册/注销「打开方式」中的 OpenClass 入口（需在打包为 exe 后调用）。"""
        from .system.shell_integration import set_openwith

        return set_openwith(bool(enabled))

    def get_openwith_registered(self) -> bool:
        from .system.shell_integration import is_openwith

        return is_openwith()


def python_version_string() -> str:
    return ".".join(str(v) for v in sys.version_info[:3])
