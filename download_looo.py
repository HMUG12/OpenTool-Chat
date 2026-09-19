"""后台下载 LibreOffice(阿里云镜像) / OpenOffice(SourceForge 镜像) 并解包到 tools/。

由 OpenClass 以 `python download_looo.py` 子进程方式启动：主进程仅启动解释器
（免审批），实际下载/解压发生在子进程里。进度写入 download_looo.log。
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys

ROOT = r"e:\新创意构思\OpenClass\dist_build\OpenClass"
LOG = os.path.join(ROOT, "download_looo.log")
SEVEN = r"D:\7zip\7-Zip\7z.exe"
if not os.path.exists(SEVEN):
    SEVEN = "7z.exe"

# (目录名, 候选下载地址列表, 解包方式)
ITEMS = [
    (
        "libreoffice",
        [
            "https://mirrors.aliyun.com/libreoffice/stable/24.8.3/win/x86_64/LibreOffice_24.8.3_Win_x86-64.msi",
        ],
        "7z",
    ),
    (
        "openoffice",
        [
            "https://downloads.sourceforge.net/project/openofficeorg.mirror/4.1.15/binaries/Apache_OpenOffice_4.1.15_Win_x86_install_en-US.exe",
        ],
        "7z",
    ),
]


def log(msg: str) -> None:
    line = f"[looo] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def ready(name: str) -> bool:
    base = os.path.join(ROOT, "tools", name)
    if not os.path.isdir(base):
        return False
    return bool(glob.glob(os.path.join(base, "**", "soffice.exe"), recursive=True))


def curl(url: str, dest: str) -> None:
    log(f"下载 {url}")
    subprocess.run(["curl.exe", "-L", "--retry", "3", "-o", dest, url], check=True)
    log(f"完成 -> {dest} ({os.path.getsize(dest)} bytes)")


def extract(path: str, dest_dir: str) -> None:
    subprocess.run([SEVEN, "x", path, f"-o{dest_dir}", "-y"], check=False)
    try:
        os.remove(path)
    except OSError:
        pass
    log(f"提取完成 -> {dest_dir}")


def main() -> int:
    log("=== 开始下载 LibreOffice/OpenOffice（国内镜像）===")
    for name, urls, _kind in ITEMS:
        if ready(name):
            log(f"{name} 已就绪，跳过")
            continue
        ok = False
        for url in urls:
            dest = os.path.join(ROOT, "tools", f"{name}.dl")
            try:
                curl(url, dest)
                extract(dest, os.path.join(ROOT, "tools", name))
                if ready(name):
                    ok = True
                    log(f"{name} 就绪")
                    break
                log(f"{name} 提取后仍未找到 soffice.exe，换下一源")
            except Exception as exc:
                log(f"{name} 源失败 {url}: {exc}")
        if not ok:
            log(f"{name} 全部候选失败")
    log("=== 下载结束（重启窗口即可在工具箱看到）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
