"""
OpenClass 桌面宿主 —— pywebview + WebView2 + 系统托盘常驻。

设计要点：
  1. 界面由前端（React + Fluent UI）渲染，视觉一致性远好于手写 QSS；
  2. WebView2 是 Windows 10/11 的系统组件，无需打包 Chromium；
  3. 业务逻辑仍在 Python 侧，工具以独立进程运行，互不干扰；
  4. 关闭按钮 / Alt+F4 不退出进程，而是最小化到托盘（常驻后台）；
  5. 通过文件参数（右键「打开方式」）调用时，自动路由到对应集成工具。
"""
from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

import webview

from .api import Api
from .core import paths
from .system.tray import TrayIcon

WINDOW_TITLE = "OpenClass-Box"
WINDOW_SIZE = (1180, 760)
MIN_SIZE = (900, 600)
ICON = paths.app_root() / "openclass.ico"


def resolve_url(dev: bool) -> str:
    """决定加载到 WebView 的地址。

    这里返回**本地路径**而非 file:// URI，配合 webview.start(http_server=True)
    由 pywebview 内置的本地 HTTP 服务提供页面。file:// 直加载在部分设备的
    WebView2 上会因安全策略/路径编码差异而整页加载失败（界面一片黑，
    且 pywebview 注入的标题栏拖动脚本也一起失效）。
    """
    if dev:
        return "http://localhost:5173"

    index = paths.frontend_index()
    if not index.is_file():
        raise FileNotFoundError(
            "未找到前端构建产物 frontend/dist/index.html。\n"
            "请先执行：cd frontend && npm run build"
        )
    loading = index.parent / "loading.html"
    if loading.is_file():
        return str(loading)  # 先显示启动加载动画，再由 loading.html 跳转到 index.html
    return str(index)


def ensure_webview2() -> bool:
    """检测 WebView2 运行时；缺失时给出明确提示（避免只看到黑屏）。

    界面完全由 WebView2 渲染，缺它时窗口会是一片黑——与其让用户猜，
    不如直接弹窗告诉他装什么、去哪装。
    """
    if sys.platform != "win32":
        return True

    # 随包携带的固定版本运行时优先：有它就不依赖目标机是否安装 WebView2
    bundled = paths.app_root() / "WebView2Runtime"
    if (bundled / "msedgewebview2.exe").is_file():
        return True

    guid = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"  # WebView2 Runtime 官方产品码
    try:
        import winreg

        for root, sub in (
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{guid}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}"),
            (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}"),
        ):
            try:
                with winreg.OpenKey(root, sub) as key:
                    winreg.QueryValueEx(key, "pv")
                    return True
            except OSError:
                continue
    except ImportError:
        return True

    # 注册表没有时再看安装目录（部分绿色部署只落文件）
    for probe in (
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft" / "EdgeWebView" / "Application",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft" / "EdgeWebView" / "Application",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "EdgeWebView" / "Application",
    ):
        try:
            if probe.is_dir() and any(probe.iterdir()):
                return True
        except OSError:
            continue

    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            "未检测到 Microsoft Edge WebView2 运行时，程序界面无法显示。\n\n"
            "请先安装 WebView2 运行时（微软官方、免费），安装后重新打开本程序：\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
            "（使用安装包安装时会自动装好这一组件）",
            "OpenClass-Box - 缺少界面运行组件",
            0x30,  # MB_ICONWARNING
        )
    except (AttributeError, OSError):
        pass
    return False


def webview_guess_gui() -> str | None:
    """优先使用 EdgeChromium(WebView2)。"""
    return "edgechromium" if sys.platform == "win32" else None


class AppHost:
    def __init__(self) -> None:
        self.api = Api()
        self.window = None
        self.tray = TrayIcon(self._show, self._quit)

    def _show(self) -> None:
        if self.window is not None:
            self.window.show()

    def _quit(self) -> None:
        try:
            self.tray.stop()
        except Exception:
            pass
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                import os

                os._exit(0)
        else:
            import os

            os._exit(0)

    def run(
        self,
        dev: bool = False,
        debug: bool = False,
        hidden: bool = False,
        files: list[str] | None = None,
    ) -> None:
        paths.ensure_runtime_dirs()

        # 缺 WebView2 时明确提示（而不是留一个黑屏窗口）
        if not ensure_webview2():
            sys.exit(3)

        try:
            url = resolve_url(dev)
        except FileNotFoundError as exc:
            print(f"[OpenClass] {exc}", file=sys.stderr)
            sys.exit(2)

        # 随包携带的固定版本 WebView2：直接指定运行目录，彻底摆脱目标机
        # 是否安装 WebView2 的问题（pywebview 会用 BrowserExecutableFolder 加载它）
        bundled_rt = paths.app_root() / "WebView2Runtime"
        if (bundled_rt / "msedgewebview2.exe").is_file():
            webview.settings['WEBVIEW2_RUNTIME_PATH'] = str(bundled_rt)

        # frameless：仅标题栏(.oc-titlebar-drag)可拖，其余区域(按钮)正常可点
        webview.settings['DRAG_REGION_SELECTOR'] = '.oc-titlebar-drag'

        self.window = webview.create_window(
            title=WINDOW_TITLE,
            url=url,
            js_api=self.api,
            width=WINDOW_SIZE[0],
            height=WINDOW_SIZE[1],
            min_size=MIN_SIZE,
            frameless=True,
            easy_drag=False,  # 仅标题栏 RPC 拖动，避免全窗口拖动导致按钮点不动
            background_color="#1B1A19",
            text_select=False,
        )
        self.api.attach_window(self.window)
        self.api.tray_available = self.tray.available

        # 关闭 / Alt+F4 = 最小化到托盘，不退出进程
        def on_closing(e: object) -> None:
            if self.tray.available:
                setattr(e, "cancel", True)
                self.window.hide()

        self.window.events.closing += on_closing

        # 来自文件参数的调用（右键「打开方式」）→ 路由启动并仅留托盘
        def route_files() -> None:
            for f in files or []:
                try:
                    self.api.open_file_with(f)
                except Exception:
                    pass

        threading.Thread(target=self.api.refresh_tools, daemon=True).start()
        # 剪贴板网址监听：复制到风险网址时自动产生告警供前端提示
        try:
            from .core.url_watch import start as start_url_watch

            start_url_watch()
        except Exception:
            pass
        # 浏览网站自动检测：读 Chrome/Edge 历史库，发现风险网址即告警
        try:
            from .core.browser_watch import start as start_browser_watch

            start_browser_watch()
        except Exception:
            pass
        if files:
            threading.Thread(target=route_files, daemon=True).start()

        # 右键「打开方式」注册表自愈：整体移动文件夹后首次启动自动刷新路径
        try:
            from .system.shell_integration import ensure_openwith

            ensure_openwith()
        except Exception:
            pass

        self.tray.start()

        if hidden or files:
            # 注意：webview.start() 之前窗口尚未就绪，此时直接 hide() 会抛
            # "Main window failed to start"。改为窗口显示完成后再隐藏。
            def _hide_after_shown() -> None:
                try:
                    self.window.hide()
                except Exception:
                    pass

            self.window.events.shown += _hide_after_shown

        try:
            webview.start(
                debug=debug,
                http_server=True,
                private_mode=True,
                gui=webview_guess_gui(),
                icon=str(ICON) if ICON.exists() else None,
            )
        finally:
            self.tray.stop()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="OpenClass", description="开源实用工具箱")
    parser.add_argument("--dev", action="store_true", help="连接本地 vite 开发服务器")
    parser.add_argument("--debug", action="store_true", help="开启 WebView 调试")
    parser.add_argument("--hidden", action="store_true", help="启动后仅驻留系统托盘")
    parser.add_argument("files", nargs="*", help="要打开的文件路径（右键打开方式）")
    parser.add_argument("--register-openwith", action="store_true", help="注册右键「打开方式」入口后退出")
    parser.add_argument("--unregister-openwith", action="store_true", help="注销右键「打开方式」入口后退出")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.register_openwith or args.unregister_openwith:
        from .system.shell_integration import set_openwith

        ok = set_openwith(bool(args.register_openwith))
        verb = "注册" if args.register_openwith else "注销"
        print(f"[OpenClass] 右键「打开方式」{verb}: {'成功' if ok else '失败（需以 OpenClass.exe 运行）'}")
        return 0 if (ok or args.unregister_openwith) else 1

    try:
        AppHost().run(
            dev=args.dev,
            debug=args.debug,
            hidden=args.hidden,
            files=args.files or None,
        )
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
