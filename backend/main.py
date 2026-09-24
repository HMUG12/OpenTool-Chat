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
    """决定加载到 WebView 的地址。"""
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
        return loading.as_uri()  # 先显示启动加载动画，再由 loading.html 跳转到 index.html
    return index.as_uri()


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

        try:
            url = resolve_url(dev)
        except FileNotFoundError as exc:
            print(f"[OpenClass] {exc}", file=sys.stderr)
            sys.exit(2)

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
            self.window.hide()

        try:
            webview.start(
                debug=debug,
                http_server=False,
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
