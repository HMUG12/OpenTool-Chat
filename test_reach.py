"""探测 LibreOffice/OpenOffice 官方下载源是否可达（绕开被阻断的 portableapps）。"""
import subprocess

URLS = {
    "libreoffice_msi": "https://download.documentfoundation.org/libreoffice/stable/24.8.3/win/x86_64/LibreOffice_24.8.3_Win_x86-64.msi",
    "openoffice_sf": "https://sourceforge.net/projects/openoffice/files/Apache_OpenOffice_4.1.15/binaries/en-US/Apache_OpenOffice_4.1.15_Win_x86_install_en-US.exe/download",
}

with open(r"e:\新创意构思\OpenClass\reach.log", "w", encoding="utf-8") as log:
    for name, u in URLS.items():
        try:
            r = subprocess.run(
                ["curl.exe", "-k", "-I", "--max-time", "25", u],
                capture_output=True, text=True, timeout=40,
            )
            log.write(f"{name}: exit={r.returncode}\n{r.stdout[:300]}\n{r.stderr[:200]}\n\n")
        except Exception as e:
            log.write(f"{name}: ERR {e}\n\n")
    log.write("done\n")
