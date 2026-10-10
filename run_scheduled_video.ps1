param(
    [ValidateSet("normal", "shorts")]
    [string]$VideoType = "shorts",
    [string]$Topic = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

$PipelineArgs = @("pipeline.py", "--video-type", $VideoType, "--auto-upload")
if (-not [string]::IsNullOrWhiteSpace($Topic)) {
    $PipelineArgs += @("--topic", $Topic)
}

Write-Host "Bhakti Dhun scheduled run: $VideoType"
Write-Host "Videos are uploaded automatically after rendering; no PC review dashboard."
& $Python @PipelineArgs
exit $LASTEXITCODE
