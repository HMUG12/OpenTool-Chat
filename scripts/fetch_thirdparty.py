"""
下载第三方组件到 tools/，让安装包「装完即用」。

- 从各项目 GitHub 最新 release 里挑 Windows 资产（排除 linux/mac/android 等）
- 下载到 tools/<组件>/，并写入 tool.json（含版本号，供更新检测对比）
- 走系统代理，失败只跳过该组件，不影响其它组件
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(ROOT / "backend"))

from core.updater import _system_proxy  # noqa: E402

TARGETS = {
    "flclash": "chen08209/FlClash",
    "hypomux": "Hypostasis-Cat/HypoMux",
    "seelen_ui": "eythaann/Seelen-UI",
    "autowall": "SegoCode/AutoWall",
}

INCLUDE = (".exe", ".msix", ".zip", ".7z")
EXCLUDE = (
    "linux", "macos", "darwin", "android", "arm", "aarch",
    ".deb", ".rpm", ".appimage", ".dmg", ".pkg",
    "sha256", ".sig", ".asc",
)
HEADERS = {"User-Agent": "OpenClass-Box"}


def build_opener():
    proxies = _system_proxy()
    return urllib.request.build_opener(
        urllib.request.ProxyHandler(proxies) if proxies else None
    )


def pick_asset(assets: list[dict]) -> dict | None:
    for asset in assets:
        name = (asset.get("name") or "").lower()
        if any(bad in name for bad in EXCLUDE):
            continue
        if name.endswith(INCLUDE):
            return asset
    return None


def download(opener, url: str, dest: Path) -> None:
    with opener.open(urllib.request.Request(url, headers=HEADERS), timeout=300) as resp:
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                fh.write(chunk)


def main() -> int:
    opener = build_opener()
    for key, repo in TARGETS.items():
        try:
            api = f"https://api.github.com/repos/{repo}/releases/latest"
            with opener.open(urllib.request.Request(api, headers=HEADERS), timeout=15) as resp:
                release = json.loads(resp.read())

            asset = pick_asset(release.get("assets") or [])
            if not asset:
                print(f"[skip] {key}: 未找到 Windows 资产")
                continue

            dest_dir = TOOLS / key
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / asset["name"]
            size_mb = asset.get("size", 0) / 1024 / 1024
            print(f"[get ] {key}: {asset['name']} ({size_mb:.1f} MB)")

            download(opener, asset["browser_download_url"], dest)

            tool = {
                "id": key,
                "name": key,
                "version": release.get("tag_name", ""),
                "description": f"{repo}（随包携带）",
                "category": "external",
                "kind": "external",
                "entry": asset["name"],
                "app": key,
            }
            (dest_dir / "tool.json").write_text(
                json.dumps(tool, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"[ok  ] {key} -> {dest}")
        except Exception as exc:  # noqa: BLE001
            print(f"[fail] {key}: {exc!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
