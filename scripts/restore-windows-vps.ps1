# Restore-Skript fuer Curiosity Wiki auf Windows-VPS (M6, ADR-0018).
#
# Nutzung:
#   .\restore-windows-vps.ps1 -BackupZip C:\curiosity\backups\daily\curiosity-backup-daily-20260509-030000.zip
#
# Schritte:
#   1. ZIP nach Staging entpacken.
#   2. Manifest laden, alle SHA-256 verifizieren.
#   3. Service stoppen.
#   4. Live-Verzeichnis nach c:\curiosity\rollback-<timestamp> umbenennen.
#   5. Staging-Inhalte ins Live-Verzeichnis kopieren.
#   6. Service starten.
#   7. Smoke-Test gegen /healthz/deep.
#   8. Bei Smoke-Fail: Rollback aus Schritt 4 und Service erneut starten.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupZip,
    [string]$AppRoot = "C:\curiosity\app",
    [string]$ServiceName = "curiosity-web",
    [int]$HealthPort = 8765,
    [int]$HealthTimeoutSec = 30
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupZip)) {
    Write-Error "Backup ZIP not found: $BackupZip"
    exit 1
}

$timestamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$staging = Join-Path $env:TEMP "curiosity-restore-staging-$timestamp"
$rollback = Join-Path (Split-Path $AppRoot -Parent) ("rollback-$timestamp")
$null = New-Item -ItemType Directory -Path $staging -Force

Write-Host "[restore] zip=$BackupZip"
Write-Host "[restore] staging=$staging"

# --- 1. ZIP entpacken ---
Expand-Archive -Path $BackupZip -DestinationPath $staging -Force

# --- 2. Manifest verifizieren ---
$manifestPath = Join-Path $staging "manifest.json"
if (-not (Test-Path $manifestPath)) {
    Write-Error "Manifest missing in backup; refusing to restore."
    exit 1
}
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
Write-Host "[restore] manifest schema_version=$($manifest.schema_version), files=$($manifest.files_count)"

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
    Write-Error "Backup integrity check failed:`n$($mismatches -join "`n")"
    exit 2
}
Write-Host "[restore] integrity OK ($($manifest.files_count) files)"

# --- 3. Service stoppen ---
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {
    Write-Host "[restore] stopping service $ServiceName"
    Stop-Service -Name $ServiceName -Force
    $stopDeadline = (Get-Date).AddSeconds(20)
    while ((Get-Service -Name $ServiceName).Status -ne "Stopped" -and (Get-Date) -lt $stopDeadline) {
        Start-Sleep -Milliseconds 500
    }
}

# --- 4. Rollback-Snapshot ---
if (Test-Path $AppRoot) {
    Write-Host "[restore] snapshotting current install to $rollback"
    Move-Item -Path $AppRoot -Destination $rollback
}
$null = New-Item -ItemType Directory -Path $AppRoot -Force

# --- 5. Staging -> Live (manifest.json bewusst nicht ins Live kopieren) ---
Get-ChildItem -Path $staging -Force | Where-Object { $_.Name -ne "manifest.json" } | ForEach-Object {
    Copy-Item -Recurse -Force $_.FullName -Destination $AppRoot
}

# --- 6. Service starten ---
Write-Host "[restore] starting service $ServiceName"
Start-Service -Name $ServiceName

# --- 7. Smoke-Test ---
$deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
$ok = $false
while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$HealthPort/healthz/deep" -TimeoutSec 5
        if ($resp.status -in @("ok", "degraded")) {
            $ok = $true
            Write-Host "[restore] healthz/deep status=$($resp.status)"
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ok) {
    Write-Warning "[restore] smoke test FAILED; rolling back to $rollback"
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    if (Test-Path $AppRoot) {
        Remove-Item -Recurse -Force $AppRoot
    }
    Move-Item -Path $rollback -Destination $AppRoot
    Start-Service -Name $ServiceName
    Remove-Item -Recurse -Force $staging
    Write-Error "Restore failed; rollback applied. Check service logs."
    exit 3
}

Remove-Item -Recurse -Force $staging
Write-Host "[restore] OK (rollback snapshot kept at $rollback)"
