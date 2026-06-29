# Bot WhatsApp — portable (flashdisk / HDD external)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BotDir = Join-Path $Root "kita-cuan-wa-bot"
Set-Location $BotDir

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual env belum ada di $Root\.venv" -ForegroundColor Yellow
    exit 1
}

$EnvFile = Join-Path $BotDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "Peringatan: kita-cuan-wa-bot\.env belum ada." -ForegroundColor Yellow
    Write-Host "Salin dari .env.example lalu isi SUPABASE_KEY (service_role), WA_API_KEY, GROQ_API_KEY." -ForegroundColor Yellow
}

$env:PYTHONPATH = $Root
$Port = if ($env:PORT) { $env:PORT } else { "8000" }
& $VenvPython -m uvicorn main:app --host 0.0.0.0 --port $Port --reload
