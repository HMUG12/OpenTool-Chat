# 后台下载并部署 VLC / LibreOffice / OpenOffice 便携版到 tools/ 下。
# 由 OpenClass 启动器以不等待方式调用；进度写入 download_apps.log。
$ErrorActionPreference = "SilentlyContinue"
$root = "e:\新创意构思\OpenClass"
$log = "$root\download_apps.log"
$sevenZip = "D:\7zip\7-Zip\7z.exe"
if (-not (Test-Path $sevenZip)) { $sevenZip = "7z.exe" }

function Log($m) { Add-Content -Path $log -Value "$(Get-Date -Format 'HH:mm:ss') $m" }

Log "=== 开始后台下载集成应用 ==="

# ── VLC ──
$vlcUrl = "https://download.videolan.org/pub/videolan/vlc/3.0.21/win64/vlc-3.0.21-win64.zip"
$vlcOut = "$root\tools\vlc\vlc.zip"
New-Item -ItemType Directory -Force -Path "$root\tools\vlc" | Out-Null
Log "VLC 下载中 -> $vlcUrl"
curl.exe -L --retry 2 -o $vlcOut $vlcUrl
if (Test-Path $vlcOut) {
    Log "VLC 下载完成，解压中..."
    Expand-Archive -Path $vlcOut -DestinationPath "$root\tools\vlc" -Force
    Remove-Item $vlcOut -Force
    Log "VLC 解压完成"
} else {
    Log "VLC 下载失败（URL 可能变动，可手动下载便携版到 tools\vlc）"
}

# ── LibreOffice Portable ──
$loUrl = "https://downloads.portableapps.com/portableapps/LibreOfficePortable/LibreOfficePortable_24.8.3.paf.exe"
$loOut = "$root\tools\libreoffice.paf.exe"
Log "LibreOffice 下载中 -> $loUrl"
curl.exe -L --retry 2 -o $loOut $loUrl
if (Test-Path $loOut) {
    Log "LibreOffice 下载完成，提取中..."
    & $sevenZip x $loOut -o"$root\tools\libreoffice" -y | Out-Null
    Remove-Item $loOut -Force
    Log "LibreOffice 提取完成"
} else {
    Log "LibreOffice 下载失败（URL 可能变动，可手动下载便携版到 tools\libreoffice）"
}

# ── Apache OpenOffice Portable ──
$ooUrl = "https://downloads.portableapps.com/portableapps/OpenOfficePortable/OpenOfficePortable_4.1.15.paf.exe"
$ooOut = "$root\tools\openoffice.paf.exe"
Log "OpenOffice 下载中 -> $ooUrl"
curl.exe -L --retry 2 -o $ooOut $ooUrl
if (Test-Path $ooOut) {
    Log "OpenOffice 下载完成，提取中..."
    & $sevenZip x $ooOut -o"$root\tools\openoffice" -y | Out-Null
    Remove-Item $ooOut -Force
    Log "OpenOffice 提取完成"
} else {
    Log "OpenOffice 下载失败（URL 可能变动，可手动下载便携版到 tools\openoffice）"
}

Log "=== 后台下载结束（完成后在工具箱中三项将变为可用）==="
