# scripts/dev.ps1
# Setup für lokale Entwicklung.
# Idempotent: kann mehrfach ausgeführt werden.

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[dev] Repo root: $repoRoot"

# 1. Virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "[dev] Creating virtual environment..."
    python -m venv .venv
}

# 2. Activate
$activate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
. $activate

# 3. Upgrade pip
python -m pip install --upgrade pip wheel | Out-Host

# 4. Install editable + dev extras
python -m pip install -e ".[dev]" | Out-Host

# 5. Sanity check
Write-Host ""
Write-Host "[dev] Smoke test:" -ForegroundColor Cyan
python -m curiosity_wiki --version
python -m curiosity_wiki info

Write-Host ""
Write-Host "[dev] Setup complete." -ForegroundColor Green
Write-Host "Next: .\scripts\test.ps1"
