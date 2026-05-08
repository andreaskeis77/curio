# scripts/test.ps1
# Run pytest mit -q und Standardmarker-Filter (ohne slow/llm).

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

python -m pytest -q -m "not slow and not llm"
exit $LASTEXITCODE
