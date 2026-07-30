# download-ffmpeg.ps1 — 下载 ffmpeg LGPL essentials 二进制作为 Tauri sidecar。
# 用法：在 desktop/ 目录运行 .\scripts\download-ffmpeg.ps1
# 下载后放到 src-tauri/binaries/ffmpeg-x86_64-pc-windows-msvc.exe（Tauri sidecar 命名规则）。

$ErrorActionPreference = "Stop"

$binariesDir = Join-Path $PSScriptRoot ".." "src-tauri" "binaries"
$targetName = "ffmpeg-x86_64-pc-windows-msvc.exe"
$targetPath = Join-Path $binariesDir $targetName

if (Test-Path $targetPath) {
    $size = (Get-Item $targetPath).Length / 1MB
    Write-Host "ffmpeg sidecar 已存在: $targetPath ($([math]::Round($size, 1)) MB)"
    exit 0
}

New-Item -ItemType Directory -Path $binariesDir -Force | Out-Null

Write-Host "下载 ffmpeg LGPL essentials（~80MB）..."
$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$zipPath = Join-Path $env:TEMP "ffmpeg-download.zip"

try {
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
} catch {
    Write-Error "下载失败: $_"
    Write-Host "可手动下载 $url，解压后把 bin/ffmpeg.exe 复制到 $targetPath"
    exit 1
}

Write-Host "解压..."
$extractDir = Join-Path $env:TEMP "ffmpeg-extract"
if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

$ffmpegExe = Get-ChildItem $extractDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
if (!$ffmpegExe) {
    Write-Error "压缩包里找不到 ffmpeg.exe"
    exit 1
}

Copy-Item $ffmpegExe.FullName $targetPath -Force
$size = (Get-Item $targetPath).Length / 1MB
Write-Host "ffmpeg sidecar 安装完成: $targetPath ($([math]::Round($size, 1)) MB)"

Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
