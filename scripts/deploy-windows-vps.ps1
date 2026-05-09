# Deployment-Skript fuer Curiosity Wiki auf Windows-VPS (M6, ADR-0017).
#
# Nutzung (auf der VPS, nach Bundle-Push via scp/Tailscale):
#   .\deploy-windows-vps.ps1 -BundleZip c:\curiosity\incoming\curiosity-bundle-<sha>-<ts>.zip
#
# Schritte:
#   1. Preflight: Bundle existiert, manifest.json darin gueltig.
#   2. Pre-Deploy-Backup (separates Skript).
#   3. Service stoppen.
#   4. Bundle entpacken nach Staging, Hash-Check.
#   5. Code-Inhalte ins Live-Verzeichnis kopieren.
#   6. pip install -e . im venv (idempotent).
#   7. registry init, index rebuild, readmodels rebuild.
#   8. Service starten, Smoke-Test gegen /healthz/deep.
#   9. Bei Fail: Restore aus Pre-Deploy-Backup.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$BundleZip,
    [string]$AppRoot = "C:\curiosity\app",
    [string]$ServiceName = "curiosity-web",
    [string]$BackupRoot = "C:\curiosity\backups",
    [string]$ScriptDir = $PSScriptRoot,
    [int]$HealthPort = 8765,
    [int]$HealthTimeoutSec = 60
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "[deploy] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Warning "[deploy] $msg" }

if (-not (Test-Path $BundleZip)) {
    Write-Error "Bundle ZIP not found: $BundleZip"
    exit 1
}

$timestamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$staging = Join-Path $env:TEMP "curiosity-deploy-staging-$timestamp"

# --- 1. Preflight ---
Write-Step "preflight: $BundleZip"
Expand-Archive -Path $BundleZip -DestinationPath $staging -Force
$manifestPath = Join-Path $staging "manifest.json"
if (-not (Test-Path $manifestPath)) {
    Write-Error "Bundle has no manifest.json; refusing to deploy."
    exit 1
}
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
Write-Step "manifest: schema_version=$($manifest.schema_version), files=$($manifest.files_count), package=$($manifest.package_version)"

$mismatches = @()
foreach ($entry in $manifest.files) {
    $stagedFile = Join-Path $staging $entry.path
    if (-not (Test-Path $stagedFile)) {
        $mismatches += "missing: $($entry.path)"
        continue
    }
    $actual = (Get-FileHash -Path $stagedFile -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $entry.sha256) {
        $mismatches += "hash mismatch: $($entry.path)"
    }
}
if ($mismatches.Count -gt 0) {
    Write-Error "Bundle integrity check failed:`n$($mismatches -join "`n")"
    exit 2
}

# --- 2. Pre-Deploy-Backup ---
Write-Step "pre-deploy backup"
$backupScript = Join-Path $ScriptDir "backup-windows-vps.ps1"
if (Test-Path $backupScript) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $backupScript -Reason "pre-deploy" -AppRoot $AppRoot -BackupRoot $BackupRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Pre-deploy backup failed; aborting."
        exit 3
    }
} else {
    Write-Warn "backup script not found at $backupScript - proceeding without pre-deploy backup."
}

# Letztes Pre-Deploy-Backup als potentielles Rollback merken.
$preDeployDir = Join-Path $BackupRoot "pre-deploy"
$rollbackZip = Get-ChildItem -Path $preDeployDir -Filter "curiosity-backup-pre-deploy-*.zip" -ErrorAction SilentlyContinue |
               Sort-Object LastWriteTime -Descending |
               Select-Object -First 1

# --- 3. Service stoppen ---
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {
    Write-Step "stopping service $ServiceName"
    Stop-Service -Name $ServiceName -Force
}

try {
    # --- 4. Inhalte uebernehmen (Manifest selbst nicht) ---
    Write-Step "copying bundle contents to $AppRoot"
    if (-not (Test-Path $AppRoot)) {
        $null = New-Item -ItemType Directory -Path $AppRoot -Force
    }
    Get-ChildItem -Path $staging -Force | Where-Object { $_.Name -ne "manifest.json" } | ForEach-Object {
        Copy-Item -Recurse -Force $_.FullName -Destination $AppRoot
    }

    # --- 5. pip install (idempotent) ---
    $pip = Join-Path $AppRoot ".venv\Scripts\pip.exe"
    $python = Join-Path $AppRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        Write-Step "creating venv"
        & py -3 -m venv (Join-Path $AppRoot ".venv")
    }
    Write-Step "pip install -e ."
    & $python -m pip install --quiet --upgrade pip
    & $python -m pip install --quiet -e $AppRoot
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed (exit $LASTEXITCODE)"
    }

    # --- 6. Schema-Migration + Index ---
    $env:CURIOSITY_VAULT_ROOT = $AppRoot
    Write-Step "registry init"
    & $python -m curiosity_wiki registry init
    if ($LASTEXITCODE -ne 0) { throw "registry init failed (exit $LASTEXITCODE)" }
    Write-Step "index rebuild"
    & $python -m curiosity_wiki index rebuild
    if ($LASTEXITCODE -ne 0) { throw "index rebuild failed (exit $LASTEXITCODE)" }
    Write-Step "readmodels rebuild"
    & $python -m curiosity_wiki readmodels rebuild
    if ($LASTEXITCODE -ne 0) { throw "readmodels rebuild failed (exit $LASTEXITCODE)" }

    # --- 7. Service starten ---
    Write-Step "starting service $ServiceName"
    Start-Service -Name $ServiceName

    # --- 8. Smoke ---
    Write-Step "healthz/deep smoke (timeout ${HealthTimeoutSec}s)"
    $deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
    $ok = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$HealthPort/healthz/deep" -TimeoutSec 5
            if ($resp.status -in @("ok", "degraded")) {
                Write-Step "deep status=$($resp.status), pages=$($resp.checks.pages_count.value)"
                $ok = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    if (-not $ok) {
        throw "deep health did not reach ok/degraded within $HealthTimeoutSec seconds"
    }
}
catch {
    Write-Warn "DEPLOY FAILED: $_"
    if ($rollbackZip) {
        Write-Warn "rolling back from $($rollbackZip.FullName)"
        $restoreScript = Join-Path $ScriptDir "restore-windows-vps.ps1"
        if (Test-Path $restoreScript) {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $restoreScript -BackupZip $rollbackZip.FullName -AppRoot $AppRoot -ServiceName $ServiceName -HealthPort $HealthPort
        } else {
            Write-Warn "restore script missing - manual intervention required"
        }
    } else {
        Write-Warn "no pre-deploy backup found - manual intervention required"
    }
    Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue
    exit 4
}

Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue
Write-Step "OK"
