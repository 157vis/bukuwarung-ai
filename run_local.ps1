<#
.SYNOPSIS
  Jalankan Streamlit dashboard laris.AI secara lokal dengan hot-reload.

.DESCRIPTION
  Setiap edit di file .py / .css akan langsung kelihatan di browser
  (http://localhost:8501) tanpa perlu push ke GitHub atau tunggu rebuild.

.PARAMETER Port
  Port untuk Streamlit. Default 8501.

.EXAMPLE
  .\run_local.ps1
  .\run_local.ps1 -Port 8502
#>

param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  laris.AI - Local Development Mode" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Lokasi  : $ScriptDir" -ForegroundColor Gray
Write-Host "  URL     : http://localhost:$Port" -ForegroundColor Green
Write-Host "  Mode    : Hot-reload (edit file -> auto refresh)" -ForegroundColor Green
Write-Host ""
Write-Host "  Pintasan:" -ForegroundColor Yellow
Write-Host "    Ctrl+C  - Stop server" -ForegroundColor Gray
Write-Host "    R       - Reload manual" -ForegroundColor Gray
Write-Host "    C       - Clear cache" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Cek Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python tidak ditemukan. Install Python 3.9+ dari python.org" -ForegroundColor Red
    exit 1
}

# Cek dependencies
Write-Host ""
Write-Host "Mengecek dependencies..." -ForegroundColor Yellow
$required = @("streamlit", "supabase", "pandas", "groq")
$missing = @()
foreach ($pkg in $required) {
    $found = pip show $pkg 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missing += $pkg
    }
}

if ($missing.Count -gt 0) {
    Write-Host "[WARN] Package hilang: $($missing -join ', ')" -ForegroundColor Yellow
    Write-Host "Install sekarang? (Y/N)" -ForegroundColor Yellow
    $ans = Read-Host
    if ($ans -eq "Y" -or $ans -eq "y") {
        Write-Host "Installing..." -ForegroundColor Yellow
        pip install -r requirements.txt
    } else {
        Write-Host "Lewati. Mungkin error saat import." -ForegroundColor Yellow
    }
}

# Buat folder .streamlit/secrets.toml kalau belum ada (untuk local dev)
$secretsDir = Join-Path $ScriptDir ".streamlit"
$secretsFile = Join-Path $secretsDir "secrets.toml"
if (-not (Test-Path $secretsDir)) {
    New-Item -ItemType Directory -Path $secretsDir -Force | Out-Null
}
if (-not (Test-Path $secretsFile)) {
    Write-Host ""
    Write-Host "[INFO] File secrets.toml belum ada. Streamlit akan baca dari env vars." -ForegroundColor Cyan
    Write-Host "  Untuk Supabase, set env:" -ForegroundColor Gray
    Write-Host "    `$env:SUPABASE_URL = '...'" -ForegroundColor Gray
    Write-Host "    `$env:SUPABASE_KEY = '...'" -ForegroundColor Gray
    Write-Host "    `$env:GROQ_API_KEY = '...'" -ForegroundColor Gray
    Write-Host ""
}

# Jalankan Streamlit
Write-Host ""
Write-Host "Menjalankan Streamlit di port $Port..." -ForegroundColor Green
Write-Host "Buka browser: http://localhost:$Port" -ForegroundColor Green
Write-Host ""
python -m streamlit run app.py `
    --server.port $Port `
    --server.address localhost `
    --server.headless false `
    --server.runOnSave true `
    --browser.gatherUsageStats false `
    --theme.base light
