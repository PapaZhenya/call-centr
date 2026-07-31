<#
.SYNOPSIS
    Builds and starts all services, waits for the API to become healthy,
    applies migrations, seeds the default rubric, and prints the URLs.
#>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Host "No .env file found - run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "=== Starting services (docker compose up -d --build) ===" -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "docker compose up failed - see output above." -ForegroundColor Red
    exit 1
}

Write-Host "`n-- Waiting for API to become healthy --"
$healthy = $false
$maxAttempts = 60
for ($i = 1; $i -le $maxAttempts; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/healthz" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        # not up yet - keep polling
    }
    Write-Host "  waiting for API... ($i/$maxAttempts)"
    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    Write-Host "API did not become healthy after $($maxAttempts * 2)s - check 'docker compose logs api'." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] API is healthy" -ForegroundColor Green

Write-Host "`n-- Applying database migrations --"
docker compose exec -T api alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "alembic upgrade head failed - see output above." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] migrations applied" -ForegroundColor Green

Write-Host "`n-- Seeding default rubric (idempotent) --"
docker compose exec -T api python -m scripts.seed_rubric
if ($LASTEXITCODE -ne 0) {
    Write-Host "seed_rubric.py failed - see output above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Ready ===" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  Metabase:  http://localhost:3001"
Write-Host ""
Write-Host "If no admin account exists yet, run .\scripts\create-admin.ps1"
