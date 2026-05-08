# scripts/quality-gates.ps1
# Voller Quality-Gate-Lauf mit Report nach docs/_ops/quality_gates/.

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

python tools/run_quality_gates.py
exit $LASTEXITCODE
