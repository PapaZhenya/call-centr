<#
.SYNOPSIS
    Read-only diagnostics: Docker status, container status, API/Postgres/
    Redis/Ollama reachability, disk space, RAM. Does not fix anything.
#>

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param([string]$Check, [string]$Status, [string]$Detail = "")
    $results.Add([PSCustomObject]@{ Check = $Check; Status = $Status; Detail = $Detail })
}

Write-Host "=== Call Center QA Platform - diagnostics ===" -ForegroundColor Cyan

# --- Docker engine ---
try {
    docker info | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Add-Result "Docker engine" "OK" ""
    } else {
        Add-Result "Docker engine" "DOWN" "docker info returned a non-zero exit code"
    }
} catch {
    Add-Result "Docker engine" "DOWN" "docker command not found or not running"
}

# --- Container status ---
try {
    $psOutput = docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>$null
    if ($LASTEXITCODE -eq 0 -and $psOutput) {
        Add-Result "Containers" "OK" (($psOutput -join " | "))
    } else {
        Add-Result "Containers" "UNKNOWN" "no containers found - has 'start.ps1' been run?"
    }
} catch {
    Add-Result "Containers" "UNKNOWN" "docker compose ps failed"
}

# --- API healthz ---
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/healthz" -UseBasicParsing -TimeoutSec 3
    if ($response.StatusCode -eq 200) {
        Add-Result "API (/healthz)" "OK" ""
    } else {
        Add-Result "API (/healthz)" "DOWN" "HTTP $($response.StatusCode)"
    }
} catch {
    Add-Result "API (/healthz)" "DOWN" "not reachable on http://localhost:8000"
}

# --- Postgres ---
try {
    $pgOutput = docker compose exec -T db pg_isready -U callcenter -d callcenter_qa 2>&1
    if ($LASTEXITCODE -eq 0) {
        Add-Result "Postgres" "OK" ""
    } else {
        Add-Result "Postgres" "DOWN" "$pgOutput"
    }
} catch {
    Add-Result "Postgres" "DOWN" "db container not reachable"
}

# --- Redis ---
try {
    $redisOutput = docker compose exec -T redis redis-cli ping 2>&1
    if ($redisOutput -match "PONG") {
        Add-Result "Redis" "OK" ""
    } else {
        Add-Result "Redis" "DOWN" "$redisOutput"
    }
} catch {
    Add-Result "Redis" "DOWN" "redis container not reachable"
}

# --- Ollama ---
try {
    $ollamaResponse = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3
    $tags = ($ollamaResponse.Content | ConvertFrom-Json).models | ForEach-Object { $_.name }
    if ($tags) {
        Add-Result "Ollama" "OK" ("models: " + ($tags -join ", "))
    } else {
        Add-Result "Ollama" "OK" "reachable, but no models pulled yet - run download-models.ps1"
    }
} catch {
    Add-Result "Ollama" "DOWN" "not reachable on http://localhost:11434 - is it installed and running?"
}

# --- Disk space ---
try {
    $drive = (Get-Item $root).PSDrive.Name
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='${drive}:'"
    $freeGb = [math]::Round($disk.FreeSpace / 1GB, 1)
    $totalGb = [math]::Round($disk.Size / 1GB, 1)
    Add-Result "Disk space ($drive`:)" "INFO" "$freeGb GB free of $totalGb GB"
} catch {
    Add-Result "Disk space" "UNKNOWN" "could not query disk info"
}

# --- RAM ---
try {
    $mem = Get-CimInstance Win32_ComputerSystem
    $totalRamGb = [math]::Round($mem.TotalPhysicalMemory / 1GB, 1)
    Add-Result "Total RAM" "INFO" "$totalRamGb GB (16 GB min, 32 GB recommended for a 7B+ local LLM)"
} catch {
    Add-Result "Total RAM" "UNKNOWN" "could not query RAM info"
}

Write-Host ""
$results | Format-Table -AutoSize -Wrap
