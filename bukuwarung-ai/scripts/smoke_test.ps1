# Smoke test portable - jalankan dari USB / laptop baru
# Usage: .\scripts\smoke_test.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== BukuWarung-AI Smoke Test ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw "Python tidak ditemukan. Install Python 3.11+" }
python --version

if (-not (Test-Path ".venv")) {
    Write-Host "Membuat venv..." -ForegroundColor Yellow
    python -m venv .venv
}
& .\.venv\Scripts\pip.exe install -q -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "WARN: .env dibuat dari example - isi API keys sebelum production!" -ForegroundColor Yellow
}

$job = Start-Job -ScriptBlock {
    Set-Location $using:Root
    & .\.venv\Scripts\python.exe main.py 2>&1
}

Start-Sleep -Seconds 5

try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 10
    Write-Host "Health: $($resp.status) v$($resp.version)" -ForegroundColor Green

    $stats = Invoke-RestMethod -Uri "http://127.0.0.1:8000/stats" -Method Get -TimeoutSec 10
    Write-Host "Stats OK: total_messages=$($stats.total_messages)" -ForegroundColor Green

    $body = '{"sender":"628119999999","message":"halo smoke test"}'
    $wh = Invoke-RestMethod -Uri "http://127.0.0.1:8000/webhook-whatsapp" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 15
    Write-Host "Webhook: $($wh.status) agent=$($wh.agent)" -ForegroundColor Green

    Write-Host ""
    Write-Host "=== SMOKE TEST PASSED ===" -ForegroundColor Green
}
catch {
    Write-Host "SMOKE TEST FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Receive-Job $job
    exit 1
}
finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}
