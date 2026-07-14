# Build V-Guard Windows distribution (PyInstaller onedir)
# Requires: pip install pyinstaller  (in requirements.txt)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== V-Guard Windows build ===" -ForegroundColor Cyan

if (Test-Path ".\dist\VGuard") {
    Write-Host "Removing previous dist\VGuard..." -ForegroundColor Yellow
    try {
        Remove-Item ".\dist\VGuard" -Recurse -Force -ErrorAction Stop
    } catch {
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backup = "dist\VGuard_old_$stamp"
        Write-Host "dist locked (close VGuard.exe). Renaming to $backup" -ForegroundColor DarkYellow
        Rename-Item ".\dist\VGuard" $backup -Force
    }
}
if (Test-Path ".\build\vguard") {
    Remove-Item ".\build\vguard" -Recurse -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Error "Create venv first: python -m venv venv"
}

Write-Host "Generating app icon (.ico)..." -ForegroundColor Yellow
& .\venv\Scripts\python scripts\build_app_icon.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& .\venv\Scripts\python -m PyInstaller build\vguard.spec --noconfirm --clean 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Dist = Join-Path $Root "dist\VGuard"
$ModelsDest = Join-Path $Dist "models"

Write-Host "Copying README and run instructions..." -ForegroundColor Yellow
Copy-Item "README.md" $Dist -Force
Copy-Item "docs\PACKAGING.md" $Dist -Force -ErrorAction SilentlyContinue

if (Test-Path ".\models\visual_model\open_nsfw.onnx") {
    Write-Host "Copying models (large)..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $ModelsDest | Out-Null
    Copy-Item ".\models\visual_model" (Join-Path $ModelsDest "visual_model") -Recurse -Force
    if (Test-Path ".\models\vosk") {
        Copy-Item ".\models\vosk" (Join-Path $ModelsDest "vosk") -Recurse -Force
    }
    if (Test-Path ".\models\explicit_audio") {
        Copy-Item ".\models\explicit_audio" (Join-Path $ModelsDest "explicit_audio") -Recurse -Force
    }
} else {
    Write-Host "WARN: models not found - run download scripts before distributing." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Build complete:" -ForegroundColor Green
Write-Host "  $Dist\VGuard.exe"
Write-Host ('Run from that folder. See docs/PACKAGING.md')
