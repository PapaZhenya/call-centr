<#
.SYNOPSIS
    One-time environment setup: checks prerequisites, creates .env, generates
    a real JWT secret. Safe to re-run.
#>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Call Center QA Platform - setup ===" -ForegroundColor Cyan

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$allOk = $true

Write-Host "`n-- Checking prerequisites --"

if (Test-CommandExists "docker") {
    Write-Host "[OK] docker found" -ForegroundColor Green
} else {
    Write-Host "[MISSING] docker not found on PATH - install Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    $allOk = $false
}

if (Test-CommandExists "docker") {
    try {
        docker compose version | Out-Null
        Write-Host "[OK] docker compose available" -ForegroundColor Green
    } catch {
        Write-Host "[MISSING] 'docker compose' failed to run - update Docker Desktop" -ForegroundColor Red
        $allOk = $false
    }
}

if (Test-CommandExists "ollama") {
    Write-Host "[OK] ollama found" -ForegroundColor Green
} else {
    Write-Host "[WARN] ollama not found on PATH - QA scoring needs it. Install: https://ollama.com/download" -ForegroundColor Yellow
    Write-Host "       (not fatal - you can install it later and run download-models.ps1)"
}

$frontendDir = Join-Path (Split-Path -Parent $root) "callcenter-qa-frontend"
if (Test-Path $frontendDir) {
    Write-Host "[OK] sibling frontend directory found: $frontendDir" -ForegroundColor Green
} else {
    Write-Host "[MISSING] expected sibling directory not found: $frontendDir" -ForegroundColor Red
    Write-Host "          docker-compose.yml builds the frontend from there."
    $allOk = $false
}

Write-Host "`n-- .env file --"

$envPath = Join-Path $root ".env"
$envExamplePath = Join-Path $root ".env.example"

if (Test-Path $envPath) {
    Write-Host "[OK] .env already exists - leaving it as-is" -ForegroundColor Green
} else {
    Copy-Item $envExamplePath $envPath
    Write-Host "[OK] created .env from .env.example" -ForegroundColor Green
}

Write-Host "`n-- JWT secret --"

function New-RandomSecret {
    param([int]$Bytes = 48)
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($buffer)
    } finally {
        $rng.Dispose()
    }
    return [Convert]::ToBase64String($buffer).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

$envLines = Get-Content $envPath
$placeholder = "JWT_SECRET_KEY=change-me-in-.env-this-default-is-not-secure"
$hasPlaceholder = $envLines -match "^JWT_SECRET_KEY=change-me-in-\.env-this-default-is-not-secure\s*$"

if ($hasPlaceholder) {
    $newSecret = New-RandomSecret
    $envLines = $envLines -replace "^JWT_SECRET_KEY=.*$", "JWT_SECRET_KEY=$newSecret"
    Set-Content -Path $envPath -Value $envLines -Encoding utf8
    Write-Host "[OK] generated a real JWT_SECRET_KEY in .env" -ForegroundColor Green
} else {
    Write-Host "[OK] JWT_SECRET_KEY already customized - left untouched" -ForegroundColor Green
}

Write-Host ""
if ($allOk) {
    Write-Host "Setup complete. Next: .\scripts\start.ps1" -ForegroundColor Cyan
} else {
    Write-Host "Setup finished with missing prerequisites above - resolve them, then re-run this script." -ForegroundColor Yellow
}
