<#
.SYNOPSIS
    Creates the first admin account via POST /api/v1/auth/setup. This
    endpoint only works once - if an admin already exists, use the
    "Пользователи" (Users) page in the app to create additional accounts.
#>

$ErrorActionPreference = "Stop"
$apiBaseUrl = "http://localhost:8000"

Write-Host "=== Create first admin account ===" -ForegroundColor Cyan

try {
    $setupStatus = Invoke-RestMethod -Uri "$apiBaseUrl/api/v1/auth/setup-required" -Method Get -TimeoutSec 5
} catch {
    Write-Host "Could not reach the API at $apiBaseUrl - is it running? Try .\scripts\start.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not $setupStatus.setup_required) {
    Write-Host "An admin account already exists." -ForegroundColor Yellow
    Write-Host "To create additional users (with any of the 7 roles), log in and use the" -ForegroundColor Yellow
    Write-Host "'Пользователи' (Users) page at http://localhost:3000/users" -ForegroundColor Yellow
    exit 0
}

$email = Read-Host "Admin email"
$passwordSecure = Read-Host "Admin password (min 8 characters)" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($passwordSecure)
try {
    $password = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if ($password.Length -lt 8) {
    Write-Host "Password must be at least 8 characters." -ForegroundColor Red
    exit 1
}

$body = @{ email = $email; password = $password } | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "$apiBaseUrl/api/v1/auth/setup" -Method Post -Body $body -ContentType "application/json"
    Write-Host "[OK] Admin account created for $email" -ForegroundColor Green
    Write-Host "Log in at http://localhost:3000/login"
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 409) {
        Write-Host "Setup was already completed by someone else in the meantime." -ForegroundColor Yellow
    } else {
        Write-Host "Failed to create admin account: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
