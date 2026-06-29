# Jalankan dari folder mana pun — path relatif ke lokasi script ini.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual env belum ada. Jalankan:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor Cyan
    Write-Host "  .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Cyan
    exit 1
}

if (-not (Test-Path (Join-Path $Root ".streamlit\secrets.toml"))) {
    Write-Host "Peringatan: .streamlit\secrets.toml belum ada." -ForegroundColor Yellow
    Write-Host "Salin dari .streamlit\secrets.toml.example lalu isi key Supabase/Groq." -ForegroundColor Yellow
}

& $VenvPython -m streamlit run app.py
