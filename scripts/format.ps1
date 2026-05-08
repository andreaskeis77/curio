# scripts/format.ps1
# ruff format anwenden auf src, tests, tools.

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

python -m ruff format src tests tools
exit $LASTEXITCODE
