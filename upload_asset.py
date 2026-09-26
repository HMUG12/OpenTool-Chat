"""
把安装包上传到 GitHub Release 附件（临时脚本，用完即删）。

说明：432MB 附件走代理上传耗时较长，脚本带自动重试；
先读入内存再一次性发送（64 位进程内存足够，且避免 chunked 传输被拒）。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from publish_release import RELEASE_ID, REPO, read_credential, system_proxy

ROOT = Path(__file__).resolve().parent
ASSET = ROOT / "installer" / "OpenClass-Box_Setup.exe"
MAX_TRIES = 3


def upload() -> int:
    token = read_credential("git:https://github.com")
    if not token:
        print("未读取到凭据")
        return 1
    if not ASSET.is_file():
        print(f"找不到安装包：{ASSET}")
        return 1

    size = ASSET.stat().st_size
    print(f"安装包：{ASSET.name} · {size / 1048576:.1f} MB", flush=True)

    proxies = system_proxy()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(proxies) if proxies else urllib.request.ProxyHandler({})
    )
    url = (
        f"https://uploads.github.com/repos/{REPO}/releases/{RELEASE_ID}"
        f"/assets?name={ASSET.name}"
    )

    for attempt in range(1, MAX_TRIES + 1):
        print(f"第 {attempt} 次上传（可能需要几分钟）…", flush=True)
        started = time.time()
        try:
            payload = ASSET.read_bytes()
            request = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"token {token}",
                    "User-Agent": "OpenClass-Box",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(size),
                },
            )
            with opener.open(request, timeout=3600) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            print(f"上传成功：{data.get('browser_download_url')}")
            print(f"耗时 {time.time() - started:.0f} 秒")
            return 0
        except urllib.error.HTTPError as exc:
            print(f"失败 {exc.code}: {exc.read().decode('utf-8', 'ignore')[:300]}")
        except (OSError, ValueError) as exc:
            print(f"失败: {exc}")
        time.sleep(5)
    return 1


if __name__ == "__main__":
    raise SystemExit(upload())
