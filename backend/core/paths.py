"""
统一路径管理 —— 整个应用唯一的路径真相来源。

开发模式  : 项目根目录
打包模式  : 可执行文件所在目录（绿色便携，不写 %APPDATA%）

这里刻意不做 `sys._MEIPASS` 分支：工具箱要求「拷贝到哪里都能跑」，
因此运行时数据与工具目录必须始终跟随 exe，而不是塞进临时解压目录。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

IS_FROZEN: bool = getattr(sys, "frozen", False)


def app_root() -> Path:
    """程序根目录。"""
    if IS_FROZEN:
        return Path(sys.executable).resolve().parent
    # backend/core/paths.py → core → backend → 根
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def tools_dir() -> Path:
    """外部工具与插件的根目录。"""
    return resource_path("tools")


_data_root_cache: Path | None = None


def _is_writable(path: Path) -> bool:
    """真实写测试：目录存在不代表可写（Program Files 下就是只读）。"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".oc_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def data_root() -> Path:
    """可写数据目录（配置 / 壁纸 / 安全事件 / 收发文件都放这里）。

    优先级：
      1. **可移动介质（U 盘）上的 data/** —— 便携急救模式：配置跟着 U 盘走，
         插到任何一台电脑都是同一套设置，拔走后不在对方机器留痕；
      2. 程序目录下的 data/ —— 绿色版便携；
      3. %LOCALAPPDATA%\\OpenClass-Box —— 安装到 Program Files 这类
         受保护位置时的回退（「设置无法保存」的根因修复）。
    """
    global _data_root_cache
    if _data_root_cache is not None:
        return _data_root_cache

    portable = app_root() / "data"

    # ① U 盘等可移动介质优先：让数据随介质移动
    try:
        from .portable import is_portable_media

        on_removable = is_portable_media()
    except Exception:
        on_removable = False

    if on_removable and _is_writable(portable):
        _data_root_cache = portable
        return portable

    if _is_writable(portable):
        _data_root_cache = portable
        return portable

    fallback = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "OpenClass-Box"
    if not _is_writable(fallback):
        fallback = Path.home() / ".openclass-box"
        fallback.mkdir(parents=True, exist_ok=True)
    _data_root_cache = fallback
    return fallback


def config_dir() -> Path:
    """用户配置与运行时数据目录（保证可写）。"""
    return data_root()


def frontend_dist() -> Path:
    """前端构建产物目录。

    打包态（PyInstaller 6.x onedir）下数据被放到 _internal（sys._MEIPASS），
    因此前端产物位于 <_MEIPASS>/frontend/dist；tools/data 仍跟随 exe 目录。
    """
    if IS_FROZEN:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "frontend" / "dist"
    return resource_path("frontend", "dist")


def frontend_index() -> Path:
    return frontend_dist() / "index.html"


def config_file() -> Path:
    return config_dir() / "app_config.json"


def ensure_runtime_dirs() -> None:
    """确保可写目录存在（失败不阻断启动）。"""
    for d in (tools_dir(), config_dir()):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
