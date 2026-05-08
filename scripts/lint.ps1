# scripts/lint.ps1
# Ruff check + format-check über src, tests, tools.

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[lint] ruff check..." -ForegroundColor Cyan
python -m ruff check src tests tools
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[lint] ruff format --check..." -ForegroundColor Cyan
python -m ruff format --check src tests tools
exit $LASTEXITCODE
