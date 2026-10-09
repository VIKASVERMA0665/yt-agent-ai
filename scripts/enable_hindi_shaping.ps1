# Enable/test Pillow's Windows RAQM runtime for Hindi/Devanagari shaping.
# Run from repository root: powershell -ExecutionPolicy Bypass -File .\scripts\enable_hindi_shaping.ps1
$ErrorActionPreference = "Stop"
$repoRoot = (Get-Location).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$dest = Join-Path $repoRoot ".venv\Scripts"
if (-not (Test-Path $python)) { throw "Project virtual environment not found. Run this from C:\Users\vikas\yt-agent-ai." }

# Show the exact Pillow build before changing anything.
Write-Host "Pillow diagnostic before setup:" -ForegroundColor Cyan
& $python -c "import PIL; from PIL import features; print('Pillow:', PIL.__version__); print('RAQM:', features.check_feature('raqm'))"
if ($LASTEXITCODE -ne 0) { throw "Python/Pillow diagnostic failed." }
$before = & $python -c "from PIL import features; print(int(features.check_feature('raqm')))"
if ($before.Trim() -eq "1") {
    Write-Host "RAQM is already enabled; no changes needed." -ForegroundColor Green
    exit 0
}

$msysRoot = "C:\msys64"
$bash = Join-Path $msysRoot "usr\bin\bash.exe"
if (-not (Test-Path $bash)) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) { throw "MSYS2 is missing and winget is unavailable. Install MSYS2 from https://www.msys2.org/ then rerun." }
    Write-Host "Installing MSYS2..." -ForegroundColor Cyan
    winget install --id MSYS2.MSYS2 --exact --accept-package-agreements --accept-source-agreements
    if (-not (Test-Path $bash)) { throw "MSYS2 was installed. Close and reopen PowerShell, then run this script again." }
}

Write-Host "Installing FriBiDi in MSYS2..." -ForegroundColor Cyan
& $bash -lc "pacman -Sy --noconfirm mingw-w64-x86_64-fribidi"
if ($LASTEXITCODE -ne 0) { throw "MSYS2 failed to install FriBiDi. See the pacman output." }

$mingwBin = Join-Path $msysRoot "mingw64\bin"
if (-not (Test-Path $mingwBin)) { throw "Expected MSYS2 MinGW folder not found: $mingwBin" }

# Copy all known FriBiDi DLL names, not just the first one found.
$copied = @()
foreach ($name in @("libfribidi-0.dll", "fribidi-0.dll", "fribidi.dll")) {
    $source = Join-Path $mingwBin $name
    if (Test-Path $source) {
        Copy-Item $source $dest -Force
        $copied += $name
        Write-Host "Copied $name"
    }
}
if ($copied.Count -eq 0) { throw "No FriBiDi DLL found in $mingwBin." }

# FriBiDi packages can rely on MinGW runtime DLLs; place available dependencies beside python.exe.
foreach ($name in @("libgcc_s_seh-1.dll", "libwinpthread-1.dll", "libiconv-2.dll", "libintl-8.dll")) {
    $source = Join-Path $mingwBin $name
    if (Test-Path $source) { Copy-Item $source $dest -Force }
}

Write-Host ""
Write-Host "Rechecking Pillow RAQM..." -ForegroundColor Cyan
& $python -c "import os; from PIL import features; print('RAQM:', features.check_feature('raqm')); print('Pillow features:', features.get_supported_features())"
if ($LASTEXITCODE -ne 0) { throw "Could not run Pillow feature diagnostic." }
$after = & $python -c "from PIL import features; print(int(features.check_feature('raqm')))"
if ($after.Trim() -ne "1") {
    Write-Host "RAQM is still disabled in this Pillow build/runtime. Do NOT rerender yet." -ForegroundColor Yellow
    Write-Host "Copy and send the full diagnostic output above; this result means DLL copying alone was insufficient." -ForegroundColor Yellow
    exit 2
}
Write-Host "SUCCESS: RAQM is enabled. Hindi captions can now use proper shaping." -ForegroundColor Green
