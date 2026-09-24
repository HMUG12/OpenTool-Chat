"""
打包为 onedir 绿色版：生成 dist_build/OpenClass-Box/OpenClass-Box.exe。

设计立场（图吧式工具箱）：
  - onedir 而非 onefile：避免每次启动全量解压到临时目录导致的十几秒冷启动；
  - 运行时数据与 tools/ 跟随 exe 目录，拷到 U 盘/任意机器即可运行；
  - 不把 7z/VLC/LibreOffice 打进包，运行时按需发现本机已装或 tools/ 便携版。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist_build"
BUILD = ROOT / "build_build"

SEP = os.pathsep  # Windows 上为 ';'


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)

    # PyInstaller 输出前会删除已存在的目标目录，而该目录通常有数千个文件，
    # 会被安全删除保护拦截（批量删除需确认）导致打包直接失败。
    # 这里先把旧产物重命名挪开，让目标路径保持"不存在"，绕开批量删除。
    out_dir = DIST / "OpenClass-Box"
    if out_dir.exists():
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_dir.rename(DIST / f"OpenClass-Box_old_{stamp}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "OpenClass-Box",
        "--onedir",
        "--noconsole",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST}",
        f"--workpath={BUILD}",
        "--add-data",
        f"{ROOT / 'frontend' / 'dist'}{SEP}frontend/dist",
        # 业务模块
        "--hidden-import",
        "backend",
        "--collect-submodules",
        "backend",
        # WebView2 渲染层
        "--hidden-import",
        "webview",
        "--collect-submodules",
        "webview",
        "--collect-data",
        "webview",
        # 托盘 / 图标
        "--collect-submodules",
        "PIL",
        "--icon",
        str(ROOT / "openclass.ico"),
        # 注册表与窗口集成
        "--hidden-import",
        "win32api",
        "--hidden-import",
        "win32gui",
        "--hidden-import",
        "win32con",
        str(ROOT / "main.py"),
    ]
    print("[pack] 开始打包，这可能需要几分钟…")
    try:
        subprocess.run(cmd, check=True, cwd=str(ROOT))
    except subprocess.CalledProcessError as exc:
        print(f"[pack] 打包失败：{exc}")
        return 1

    # 工具目录不交给 PyInstaller（会被塞进 _internal），直接复制到 exe 同级，
    # 保证 tools_dir() 找到，且与 exe 一起拷贝即可运行。
    dest_tools = DIST / "OpenClass-Box" / "tools"
    if dest_tools.exists():
        shutil.rmtree(dest_tools)
    shutil.copytree(ROOT / "tools", dest_tools)
    print(f"[pack] 已复制工具目录 -> {dest_tools}")

    # 应用图标：供运行期 create_window(icon=) 使用（与 exe 图标一致）
    icon_src = ROOT / "openclass.ico"
    icon_dst = DIST / "OpenClass-Box" / "openclass.ico"
    if icon_src.is_file():
        shutil.copy(icon_src, icon_dst)
        print(f"[pack] 已复制图标 -> {icon_dst}")

    exe = DIST / "OpenClass-Box" / "OpenClass-Box.exe"
    print(f"[pack] 完成：{exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
