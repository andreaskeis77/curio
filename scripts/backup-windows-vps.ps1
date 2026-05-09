# Backup-Skript fuer Curiosity Wiki auf Windows-VPS (M6, ADR-0018).
#
# Nutzung:
#   .\backup-windows-vps.ps1                       # daily
#   .\backup-windows-vps.ps1 -Reason pre-deploy
#   .\backup-windows-vps.ps1 -Reason monthly
#
# Erzeugt:
#   c:\curiosity\backups\<reason>\curiosity-backup-<reason>-<timestamp>.zip
#   und ein begleitendes manifest.json mit SHA-256 pro File.
#
# Aufbewahrung (siehe ADR-0018):
#   daily:      14 Tage
#   pre-deploy: 30 Tage
#   monthly:    12 Monate

[CmdletBinding()]
param(
    [ValidateSet("daily", "pre-deploy", "monthly")]
    [string]$Reason = "daily",
    [string]$AppRoot = "C:\curiosity\app",
    [string]$BackupRoot = "C:\curiosity\backups"
)

$ErrorActionPreference = "Stop"
$timestamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$reasonDir = Join-Path $BackupRoot $Reason
$null = New-Item -ItemType Directory -Path $reasonDir -Force

$bundleName = "curiosity-backup-$Reason-$timestamp.zip"
$bundlePath = Join-Path $reasonDir $bundleName
$staging = Join-Path $env:TEMP "curiosity-backup-staging-$timestamp"
$null = New-Item -ItemType Directory -Path $staging -Force

Write-Host "[backup] reason=$Reason target=$bundlePath"

# --- Pre-Flight ---
$freeBytes = (Get-PSDrive -Name (Split-Path $BackupRoot -Qualifier).TrimEnd(":")).Free
if ($freeBytes -lt 1GB) {
    Write-Error "Free disk space below 1 GB; aborting backup."
    exit 1
}

# --- 1. Daten sammeln ---
$includeDirs = @("wiki", "read_models", "prompts", "eval")
foreach ($dir in $includeDirs) {
    $src = Join-Path $AppRoot $dir
    if (Test-Path $src) {
        $dst = Join-Path $staging $dir
        Copy-Item -Recurse -Force $src $dst
    }
}

$pyproject = Join-Path $AppRoot "pyproject.toml"
if (Test-Path $pyproject) {
    Copy-Item -Force $pyproject (Join-Path $staging "pyproject.toml")
}

# --- 2. SQLite konsistent kopieren via VACUUM INTO ---
$sourceDb = Join-Path $AppRoot "data\registry\curiosity.sqlite"
if (Test-Path $sourceDb) {
    $dbDest = Join-Path $staging "data\registry"
    $null = New-Item -ItemType Directory -Path $dbDest -Force
    $vacuumTarget = (Join-Path $dbDest "curiosity.sqlite") -replace "\\", "/"
    & "$AppRoot\.venv\Scripts\python.exe" -c "import sqlite3; c=sqlite3.connect(r'$sourceDb'); c.execute('VACUUM INTO ?', (r'$vacuumTarget',)); c.close()"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "VACUUM INTO failed; falling back to file copy."
        Copy-Item -Force $sourceDb (Join-Path $dbDest "curiosity.sqlite")
    }
}

# --- 3. WinSW-Configs mitsichern (nicht-secret-Inhalt) ---
$serviceXml = "C:\curiosity\service\curiosity-web.xml"
if (Test-Path $serviceXml) {
    $rtDir = Join-Path $staging "runtime"
    $null = New-Item -ItemType Directory -Path $rtDir -Force
    Copy-Item -Force $serviceXml (Join-Path $rtDir "service.xml")
}

# --- 4. Manifest erstellen ---
$files = Get-ChildItem -Path $staging -Recurse -File
$manifestEntries = @()
$bytesTotal = 0
foreach ($f in $files) {
    $rel = $f.FullName.Substring($staging.Length + 1) -replace "\\", "/"
    $hash = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash.ToLower()
    $manifestEntries += [pscustomobject]@{
        path   = $rel
        sha256 = $hash
        bytes  = $f.Length
    }
    $bytesTotal += $f.Length
}

$manifest = [pscustomobject]@{
    schema_version = 1
    created_at     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    host           = $env:COMPUTERNAME
    reason         = $Reason
    bytes_total    = $bytesTotal
    files_count    = $manifestEntries.Count
    files          = $manifestEntries
}
$manifestPath = Join-Path $staging "manifest.json"
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -Path $manifestPath

# --- 5. ZIP packen ---
if (Test-Path $bundlePath) {
    Remove-Item -Force $bundlePath
}
Compress-Archive -Path "$staging\*" -DestinationPath $bundlePath -CompressionLevel Optimal

Write-Host "[backup] wrote $bundlePath ($([math]::Round($bytesTotal/1KB,1)) KB, $($manifestEntries.Count) files)"

# --- 6. Aufbewahrung ---
$retentionDays = switch ($Reason) {
    "daily"      { 14 }
    "pre-deploy" { 30 }
    "monthly"    { 365 }
    default      { 14 }
}
$cutoff = (Get-Date).AddDays(-$retentionDays)
Get-ChildItem -Path $reasonDir -Filter "curiosity-backup-*.zip" |
    Where-Object { $_.LastWriteTime -lt $cutoff } |
    ForEach-Object {
        Write-Host "[backup] expiring $($_.Name) (older than $retentionDays days)"
        Remove-Item -Force $_.FullName
    }

# --- 7. Cleanup Staging ---
Remove-Item -Recurse -Force $staging

Write-Host "[backup] OK"
