# Off-Site-Pull-Skript fuer Andreas-Laptop (M6, ADR-0018).
#
# Holt Backup-ZIPs additiv von der VPS via Tailscale-SMB nach lokal.
# Loescht NICHTS — Off-Site soll sich nie versehentlich leeren.
#
# Voraussetzungen:
#   - Tailscale aktiv, VPS im selben Tailnet, SMB-Share \\<host>\backups$.
#   - Lokales Verzeichnis existiert (wird sonst angelegt).

[CmdletBinding()]
param(
    [string]$VpsHost = "vps-curiosity",
    [string]$RemoteShare = "backups$",
    [string]$LocalDir = "C:\curiosity\offsite-backups"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $LocalDir)) {
    $null = New-Item -ItemType Directory -Path $LocalDir -Force
}

$remote = "\\$VpsHost\$RemoteShare"
Write-Host "[pull] $remote -> $LocalDir"

# /E: rekursiv, /XO: nur kopieren wenn neuer, /R:2 W:5: kurze Retries.
# Kein /MIR — wir loeschen nichts.
robocopy $remote $LocalDir /E /XO /R:2 /W:5 /NFL /NDL /NJH

if ($LASTEXITCODE -ge 8) {
    Write-Error "robocopy reported failure (exit $LASTEXITCODE)."
    exit 1
}

Write-Host "[pull] OK"
