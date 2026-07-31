<#
.SYNOPSIS
    Stops all services. Data in Docker volumes (Postgres, audio, models) is
    preserved unless -RemoveVolumes is passed.

.PARAMETER RemoveVolumes
    Also deletes the named volumes (Postgres data, audio storage, cached
    Whisper models). Destructive - asks for confirmation.
#>

param(
    [switch]$RemoveVolumes
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($RemoveVolumes) {
    Write-Host "This will permanently delete the Postgres database, uploaded audio, and cached models." -ForegroundColor Yellow
    $confirm = Read-Host "Type 'yes' to confirm"
    if ($confirm -ne "yes") {
        Write-Host "Aborted - nothing was removed."
        exit 0
    }
    Write-Host "=== Stopping services and removing volumes ===" -ForegroundColor Cyan
    docker compose down -v
} else {
    Write-Host "=== Stopping services (data volumes preserved) ===" -ForegroundColor Cyan
    docker compose down
}
