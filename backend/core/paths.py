"""
统一路径管理 —— 整个应用唯一的路径真相来源。

开发模式  : 项目根目录
打包模式  : 可执行文件所在目录（绿色便携，不写 %APPDATA%）

这里刻意不做 `sys._MEIPASS` 分支：工具箱要求「拷贝到哪里都能跑」，
因此运行时数据与工具目录必须始终跟随 exe，而不是塞进临时解压目录。
"""
from __future__ import annotations

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


def config_dir() -> Path:
    """用户配置与运行时数据目录。"""
    return resource_path("data")


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
    """确保可写目录存在。"""
    for d in (tools_dir(), config_dir()):
        d.mkdir(parents=True, exist_ok=True)
