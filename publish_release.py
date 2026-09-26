"""
发布 GitHub Release（临时脚本）。

放在这里的原因：PowerShell 5.1 的 ConvertTo-Json / Invoke-RestMethod 在发送
中文 JSON 时编码不可靠（实测把 1.5KB 的说明判成超过 12.5 万字符而上报 422）。
Python 的 UTF-8 处理没有这类坑，因此用它完成发布，用完即删。
"""
from __future__ import annotations

import ctypes
import json
import urllib.error
import urllib.request
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "HMUG12/OpenClass-Box"
RELEASE_ID = 397112933
TARGET = "git:https://github.com"
CRED_TYPE_GENERIC = 1


class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def read_credential(target: str) -> str:
    """从 Windows 凭证管理器读取 git 保存的 GitHub token。"""
    advapi = ctypes.windll.advapi32
    ptr = ctypes.POINTER(CREDENTIAL)()
    if not advapi.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(ptr)):
        return ""
    try:
        cred = ptr.contents
        size = int(cred.CredentialBlobSize)
        if size <= 0:
            return ""
        raw = ctypes.string_at(cred.CredentialBlob, size)
        return raw.decode("utf-16-le", "ignore")
    finally:
        advapi.CredFree(ptr)


def system_proxy() -> dict[str, str]:
    """读取系统代理（GitHub 访问通常需要走代理）。"""
    proxies: dict[str, str] = {}
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
            server = winreg.QueryValueEx(key, "ProxyServer")[0]
        if enable and server:
            for part in str(server).split(";"):
                part = part.strip()
                if not part:
                    continue
                scheme, addr = part.split("=", 1) if "=" in part else ("http", part)
                addr = addr if "://" in addr else f"http://{addr}"
                proxies[scheme.strip().lower()] = addr
    except (OSError, ImportError):
        pass
    return proxies


def main() -> int:
    token = read_credential(TARGET)
    if not token:
        print("未读取到 GitHub 凭据")
        return 1
    print(f"凭据长度: {len(token)}")

    notes = (ROOT / "release_notes.md").read_text(encoding="utf-8")
    payload = json.dumps(
        {
            "name": "OpenClass-Box v0.1.3 Beta",
            "body": notes,
            "prerelease": True,
            "draft": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    print(f"发布说明: {len(notes)} 字符 / {len(payload)} 字节")

    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/{RELEASE_ID}",
        data=payload,
        method="PATCH",
        headers={
            "Authorization": f"token {token}",
            "User-Agent": "OpenClass-Box",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    proxies = system_proxy()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(proxies) if proxies else urllib.request.ProxyHandler({})
    )
    try:
        with opener.open(request, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print("发布成功:", data.get("html_url"))
        print("draft:", data.get("draft"), "| prerelease:", data.get("prerelease"))
        return 0
    except urllib.error.HTTPError as exc:
        print(f"失败 {exc.code}: {exc.read().decode('utf-8', 'ignore')[:400]}")
        return 1
    except (OSError, ValueError) as exc:
        print("失败:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
