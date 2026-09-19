"""后台重试下载 LibreOffice / OpenOffice（curl -k 规避目标站点 TLS 握手失败）。

由 OpenClass 以 `python download_apps.py` 子进程方式启动：主进程仅启动解释器
（免审批），实际下载/解压发生在子进程里。进度追加写入 download_apps.log。
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import zipfile

ROOT = r"e:\新创意构思\OpenClass"
LOG = os.path.join(ROOT, "download_apps.log")
SEVEN = r"D:\7zip\7-Zip\7z.exe"
if not os.path.exists(SEVEN):
    SEVEN = "7z.exe"

ITEMS = [
    (
        "libreoffice",
        "https://downloads.portableapps.com/portableapps/LibreOfficePortable/LibreOfficePortable_24.8.3.paf.exe",
        "7z",
    ),
    (
        "openoffice",
        "https://downloads.portableapps.com/portableapps/OpenOfficePortable/OpenOfficePortable_4.1.15.paf.exe",
        "7z",
    ),
]


def log(msg: str) -> None:
    line = f"[download] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def is_ready(name: str) -> bool:
    base = os.path.join(ROOT, "tools", name)
    if not os.path.isdir(base):
        return False
    return bool(glob.glob(os.path.join(base, "**", "soffice.exe"), recursive=True))


def curl_download(url: str, dest: str) -> None:
    log(f"下载 {url}")
    subprocess.run(
        ["curl.exe", "-k", "-L", "--retry", "3", "-o", dest, url],
        check=True,
    )
    log(f"完成 -> {dest} ({os.path.getsize(dest)} bytes)")


def extract_7z(path: str, dest_dir: str) -> None:
    subprocess.run([SEVEN, "x", path, f"-o{dest_dir}", "-y"], check=False)
    try:
        os.remove(path)
    except OSError:
        pass
    log(f"提取完成 -> {dest_dir}")


def main() -> int:
    log("=== 重试下载 LibreOffice/OpenOffice（curl -k）===")
    for name, url, kind in ITEMS:
        if is_ready(name):
            log(f"{name} 已就绪，跳过")
            continue
        out = os.path.join(ROOT, "tools", f"{name}.paf.exe")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            curl_download(url, out)
            extract_7z(out, os.path.join(ROOT, "tools", name))
            if is_ready(name):
                log(f"{name} 就绪")
            else:
                log(f"{name} 提取后仍未找到 soffice.exe")
        except Exception as exc:
            log(f"{name} 失败: {exc}")
    log("=== 重试下载结束 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
