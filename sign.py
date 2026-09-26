"""
代码签名 —— SignPath 正式证书下来之前的临时方案。

原理与边界（重要，避免误解）：

  ✅ 自签名证书能做到：
    1. exe / 安装包拥有真实数字签名（属性 → 数字签名可见）；
    2. **在本机导入信任根后**，Windows 不再提示「未知发布者」，
       杀软与 SmartScreen 的启发式误报也会明显减少；
    3. 完整版本信息 + 签名，显著降低「疑似风险程序」判定。

  ❌ 自签名证书做不到：
    - 别人的电脑上没有这把根证书，仍会提示未知发布者。
      要彻底解决只能等权威 CA 签发的证书（SignPath 免费开源证书、
      Certum 开源证书或 Azure Trusted Signing）。

本脚本流程：
  init  → 生成自签名代码签名证书（3 年）→ 导出 pfx/cer → 导入本机受信任根
  sign  → 给 dist_build 与 installer 下的产物签名
  trust → 仅把已有 cer 导入本机受信任根（换机器部署时用）
  info  → 查看证书与签名状态

注意：Windows 的受信任根写入必须通过 certutil 完成
（.NET 的 Import-Certificate 在非交互环境会报「不允许使用 UI」）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SIGN_DIR = ROOT / "signing"
CERT_SUBJECT = "CN=HMUG12, O=OpenClass-Box, OU=Open Source, C=CN"
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _ps(script: str, timeout: float = 120) -> str:
    """执行 PowerShell 并安全解码输出。"""
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"__ERROR__ {exc}"
    raw = proc.stdout or b""
    if not raw:
        return ""
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "ignore")


def _thumbprint() -> str:
    out = _ps(
        "Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Subject -like '*HMUG12*' -and $_.HasPrivateKey } | "
        "Sort-Object NotAfter -Descending | Select-Object -First 1 -ExpandProperty Thumbprint"
    )
    lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def certificate_exists() -> bool:
    return bool(_thumbprint())


def trust_root(cer_path: Path | None = None) -> bool:
    """把证书导入当前用户的「受信任的根证书颁发机构」。

    必须用 certutil：.NET 的 Import-Certificate 在非交互环境会因
    需要 UI 确认而失败；certutil 则可以直接写入用户存储。
    """
    cer = cer_path or (SIGN_DIR / "OpenClass-Box.cer")
    if not cer.is_file():
        print(f"[sign] 找不到证书文件：{cer}")
        return False
    try:
        proc = subprocess.run(
            ["certutil.exe", "-user", "-addstore", "-f", "Root", str(cer)],
            capture_output=True,
            timeout=60,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[sign] 导入信任根失败：{exc}")
        return False
    ok = proc.returncode == 0
    print(f"[sign] 信任根导入：{'成功' if ok else '失败（返回码 %s）' % proc.returncode}")
    return ok


def init_certificate() -> bool:
    """生成自签名证书 → 导出 pfx/cer → 导入本机受信任根。"""
    SIGN_DIR.mkdir(parents=True, exist_ok=True)
    pfx = SIGN_DIR / "OpenClass-Box.pfx"
    cer = SIGN_DIR / "OpenClass-Box.cer"
    script = f"""
$ErrorActionPreference = 'Stop'
$subject = '{CERT_SUBJECT}'
$existing = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert -ErrorAction SilentlyContinue |
            Where-Object {{ $_.Subject -eq $subject -and $_.HasPrivateKey }}
if (-not $existing) {{
  # 指定传统 CSP：部分环境（尤其非交互）下 CNG 密钥会导致签名接口失败
  $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
    -CertStoreLocation Cert:\\CurrentUser\\My -KeyAlgorithm RSA -KeyLength 2048 `
    -Provider 'Microsoft Enhanced RSA and AES Cryptographic Provider' `
    -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(3)
  Write-Output ('CREATED ' + $cert.Thumbprint)
}} else {{
  $cert = $existing | Sort-Object NotAfter -Descending | Select-Object -First 1
  Write-Output ('EXISTS ' + $cert.Thumbprint)
}}
$pwd = ConvertTo-SecureString -String 'openclass' -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath '{pfx}' -Password $pwd | Out-Null
Export-Certificate -Cert $cert -FilePath '{cer}' -Type CERT -Force | Out-Null
Write-Output 'EXPORTED'
"""
    out = _ps(script, timeout=180)
    print(out.strip() or "（无输出）")
    if "EXPORTED" not in out:
        return False
    return trust_root(cer)


def sign_file(path: Path, timestamp: bool = False) -> bool:
    """给单个文件签名。

    timestamp=True 会向公共时间戳服务器取时间戳（需要联网）；
    自签名临时方案默认关闭，避免代理环境下签名失败。
    """
    if not path.is_file():
        print(f"[sign] 文件不存在：{path}")
        return False

    thumb = _thumbprint()
    if not thumb:
        print("[sign] 未找到代码签名证书，请先执行：python sign.py init")
        return False

    stamp = "-TimestampServer 'http://timestamp.digicert.com'" if timestamp else ""
    script = (
        f"$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | "
        f"Where-Object {{ $_.Thumbprint -eq '{thumb}' }} | Select-Object -First 1; "
        f"$r = Set-AuthenticodeSignature -FilePath '{path}' -Certificate $cert {stamp} -HashAlgorithm SHA256; "
        "Write-Output ('STATUS:' + $r.Status); Write-Output ('MSG:' + $r.StatusMessage)"
    )
    out = _ps(script, timeout=180)
    ok = "STATUS:Valid" in out
    if ok:
        print(f"[sign] 已签名：{path.name}")
    else:
        detail = " ".join(line.strip() for line in out.strip().splitlines() if line.strip())[:240]
        print(f"[sign] 签名未完成：{path.name} — {detail}")
    return ok


def export_cer(target: Path) -> bool:
    """把信任证书复制到指定位置（随产物分发，供其他机器导入）。"""
    source = SIGN_DIR / "OpenClass-Box.cer"
    if not source.is_file():
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        return True
    except OSError:
        return False


def installers() -> list[Path]:
    """待签名的安装包：A 端 / B 端（以及旧命名的兼容项）。"""
    return [
        ROOT / "installer" / "OpenClass-Box-A_Setup.exe",
        ROOT / "installer" / "OpenClass-Box-B_Setup.exe",
        ROOT / "installer" / "OpenClass-Box_Setup.exe",
    ]


def sign_all() -> int:
    targets: list[Path] = []
    exe = ROOT / "dist_build" / "OpenClass-Box" / "OpenClass-Box.exe"
    if exe.is_file():
        targets.append(exe)
    targets.extend(path for path in installers() if path.is_file())
    if not targets:
        print("[sign] 没有找到可签名的产物（先运行 pack.py）")
        return 1
    ok = True
    for path in targets:
        ok = sign_file(path) and ok
    if ok:
        export_cer(ROOT / "dist_build" / "OpenClass-Box" / "OpenClass-Box.cer")
    return 0 if ok else 1


def status() -> int:
    print(f"[sign] 本地证书：{_thumbprint() or '未生成（python sign.py init）'}")
    for path in [
        ROOT / "dist_build" / "OpenClass-Box" / "OpenClass-Box.exe",
        *installers(),
    ]:
        if not path.is_file():
            continue
        out = _ps(f"(Get-AuthenticodeSignature '{path}').Status")
        lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
        print(f"[sign] {path.name}: {lines[-1] if lines else '未知'}")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "info"
    if action == "init":
        raise SystemExit(0 if init_certificate() else 1)
    if action == "sign":
        raise SystemExit(sign_all())
    if action == "trust":
        raise SystemExit(0 if trust_root() else 1)
    raise SystemExit(status())
