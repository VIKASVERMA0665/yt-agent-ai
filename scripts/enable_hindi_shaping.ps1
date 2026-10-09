# Enable proper Hindi/Devanagari shaping for Pillow on Windows.
# Run from the repository root in PowerShell:
# powershell -ExecutionPolicy Bypass -File .\scripts\enable_hindi_shaping.ps1

$ErrorActionPreference = "Stop"
$repoRoot = (Get-Location).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Project virtual environment not found. Run from the yt-agent-ai folder." }

$msysRoot = "C:\msys64"
$bash = Join-Path $msysRoot "usr\bin\bash.exe"
if (-not (Test-Path $bash)) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) { throw "MSYS2 is needed. Install it from https://www.msys2.org/ and rerun this script." }
    Write-Host "Installing MSYS2 (one-time prerequisite)..." -ForegroundColor Cyan
    winget install --id MSYS2.MSYS2 --exact --accept-package-agreements --accept-source-agreements
    if (-not (Test-Path $bash)) { throw "If MSYS2 was just installed, rerun this script." }
}

Write-Host "Installing FriBiDi through the official MSYS2 package manager..." -ForegroundColor Cyan
& $bash -lc "pacman -Sy --noconfirm mingw-w64-x86_64-fribidi"
if ($LASTEXITCODE -ne 0) { throw "MSYS2 could not install FriBiDi. See the pacman error above." }

$mingwBin = Join-Path $msysRoot "mingw64\bin"
$dest = Join-Path $repoRoot ".venv\Scripts"
$required = @("libfribidi-0.dll", "fribidi-0.dll", "fribidi.dll")
$found = $false
foreach ($name in $required) {
    $source = Join-Path $mingwBin $name
    if (Test-Path $source) { Copy-Item $source $dest -Force; Write-Host "Installed $name"; $found = $true; break }
}
if (-not $found) { throw "FriBiDi DLL not found in $mingwBin." }

# Copy common MinGW runtime dependencies when present.
foreach ($name in @("libgcc_s_seh-1.dll", "libwinpthread-1.dll", "libiconv-2.dll", "libintl-8.dll")) {
    $source = Join-Path $mingwBin $name
    if (Test-Path $source) { Copy-Item $source $dest -Force }
}

Write-Host ""
Write-Host "Checking Pillow RAQM support..." -ForegroundColor Cyan
& $python -c "from PIL import features; print('RAQM:', features.check_feature('raqm'))"
if ($LASTEXITCODE -ne 0) { throw "Could not check Pillow RAQM support." }
$raqm = & $python -c "from PIL import features; print(int(features.check_feature('raqm')))"
if ($raqm.Trim() -ne "1") { throw "RAQM is still unavailable. DLL runtime dependencies may be missing; send the output above." }
Write-Host "SUCCESS: Pillow RAQM is enabled." -ForegroundColor Green
