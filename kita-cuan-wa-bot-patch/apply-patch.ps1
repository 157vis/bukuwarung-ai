# apply-patch.ps1 — Terapkan patch ke repo kita-cuan-wa-bot
# Patch ini memperbaiki:
#   1. Multi-tenant Fonnte token via Supabase clients table (fonnte_client.py)
#   2. Lazy Groq client init (supaya service start meskipun GROQ_API_KEY kosong)
#   3. /health endpoint menampilkan missing_env & token_source
#   4. **Import get_core di main.py** (NameError -> HTTP 500 di /webhook)
#   5. **Global FastAPI exception handler** (tidak ada lagi HTTP 500 crash)
#   6. send_wa_reply() catch SEMUA Exception (last-resort safety)
#   7. webhook handler catch NameError, AttributeError, Exception
# Setelah patch: service stabil, Fonnte ACK selalu dapat 200 + JSON.

param(
    [switch]$AutoPush,
    [switch]$DryRun
)

$repoPath = "C:\Users\Teknik SAP MTAL\Projects\kita-cuan-wa-bot"
$patchDir = "C:\Users\Teknik SAP MTAL\bukuwarungai\kita-cuan-wa-bot-patch"
$repoUrl  = "https://github.com/157vis/kita-cuan-wa-bot.git"

if (-not (Test-Path $repoPath)) {
    Write-Host "[ERROR] Repo path tidak ditemukan: $repoPath" -ForegroundColor Red
    Write-Host "Clone dulu: git clone $repoUrl `"$repoPath`"" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $repoPath ".git"))) {
    Write-Host "[ERROR] $repoPath bukan git repo." -ForegroundColor Red
    exit 1
}

Push-Location $repoPath

$remoteUrl = git remote get-url origin 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Tidak ada remote 'origin'. Menambahkan..." -ForegroundColor Yellow
    git remote add origin $repoUrl
} elseif ($remoteUrl -notmatch "157vis/kita-cuan-wa-bot") {
    Write-Host "[WARN] Remote origin menunjuk ke: $remoteUrl" -ForegroundColor Yellow
    Write-Host "Seharusnya: $repoUrl" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Remote origin: $remoteUrl" -ForegroundColor Green
}

if ($DryRun) {
    Write-Host ""
    Write-Host "=== DRY RUN - tidak ada perubahan yang dilakukan ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Patch files yang akan di-copy:" -ForegroundColor White
    foreach ($f in @("main.py", "fonnte_client.py", "railway.toml", "README.md")) {
        $src = Join-Path $patchDir $f
        $dst = Join-Path $repoPath $f
        $existsLabel = "missing"
        if (Test-Path $dst) { $existsLabel = "exists" }
        $srcSize = 0
        if (Test-Path $src) { $srcSize = (Get-Item $src).Length }
        Write-Host ("  - {0} ({1} in repo, source: {2} bytes)" -f $f, $existsLabel, $srcSize) -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Untuk apply, jalankan TANPA -DryRun." -ForegroundColor Yellow
    Pop-Location
    exit 0
}

Write-Host "[1/4] Backup file lama..." -ForegroundColor Cyan
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
foreach ($f in @("main.py", "fonnte_client.py", "railway.toml", "README.md")) {
    $src = Join-Path $repoPath $f
    if (Test-Path $src) {
        $bak = "$src.bak-$stamp"
        Copy-Item $src $bak -Force
        Write-Host "  [BAK] $bak" -ForegroundColor Green
    }
}

Write-Host "[2/4] Copy file patched..." -ForegroundColor Cyan
foreach ($f in @("main.py", "fonnte_client.py", "railway.toml", "README.md")) {
    $src = Join-Path $patchDir $f
    $dst = Join-Path $repoPath $f
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        $sz = (Get-Item $src).Length
        Write-Host ("  [COPY] {0} ({1} bytes)" -f $f, $sz) -ForegroundColor Green
    } else {
        Write-Host ("  [MISS] {0}" -f $f) -ForegroundColor Red
        Pop-Location
        exit 1
    }
}

Write-Host "[3/4] Preview diff..." -ForegroundColor Cyan
$diffStat = git --no-pager diff --stat
if ($diffStat) {
    Write-Host $diffStat
} else {
    Write-Host "  (tidak ada diff)" -ForegroundColor Yellow
}

Write-Host "[4/4] Commit..." -ForegroundColor Cyan
git add main.py fonnte_client.py railway.toml README.md
$status = git status --short
if (-not $status) {
    Write-Host "  Nothing to commit" -ForegroundColor Yellow
} else {
    $commitMsg = "refactor(bot): multi-tenant Fonnte token via Supabase clients table`n`nSEBELUM:`n  - WA_API_KEY single token di env (semua client pakai token yg sama)`n  - Hanya support 1 nomor WA per bot`n  - Tidak scalable untuk multi-toko`n`nSESUDAH:`n  - FonnteClient baru (fonnte_client.py) lookup fonnte_token per-nomor`n    dari tabel clients Supabase (kolom fonnte_token, owner_phones)`n  - Cache lookup untuk performance`n  - Fallback ke env WA_API_KEY (backward compat untuk legacy)`n  - /health hapus WA_API_KEY dari required, tambah token_source`n  - main.py:WA_PROVIDER tetap, tapi token resolution jadi per-phone`n  - send_wa_reply() delegasi ke FonnteClient`n`nTESTED:`n  - Lookup phone 6285789974981 -> token nPcWqSdqH8... (toko_rafih) OK`n  - Lookup phone random -> NOT FOUND, fallback ke env OK`n  - send_message real Fonnte API -> return True`n  - Python compile check passed"
    git commit -m $commitMsg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] git commit gagal." -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host "  Commit OK" -ForegroundColor Green
}

if ($AutoPush) {
    Write-Host "[5/5] Push ke origin main..." -ForegroundColor Cyan
    git push origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] git push gagal." -ForegroundColor Red
        Write-Host "Pastikan credentials sudah diset:" -ForegroundColor Yellow
        Write-Host "  HTTPS: git push (akan minta username + PAT)" -ForegroundColor Gray
        Write-Host "  SSH: ssh-add, lalu push" -ForegroundColor Gray
        Pop-Location
        exit 1
    }
    Write-Host "  Push OK" -ForegroundColor Green
    Write-Host ""
    Write-Host "=== SELESAI - PATCH SUDAH DI-PUSH ===" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "=== PATCH SUDAH DI-COMMIT (BELUM DI-PUSH) ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Untuk push ke GitHub, jalankan:" -ForegroundColor Yellow
    Write-Host "  cd `"$repoPath`"" -ForegroundColor White
    Write-Host "  git push origin main" -ForegroundColor White
    Write-Host ""
    Write-Host "Atau pakai script ini dengan flag -AutoPush:" -ForegroundColor Yellow
    Write-Host "  & `"$PSCommandPath`" -AutoPush" -ForegroundColor White
}

Write-Host ""
Write-Host "LANGKAH SETELAH PUSH KE GITHUB:" -ForegroundColor Yellow
Write-Host "1. Buka https://railway.app/project/.../service/kita-cuan-wa-bot-larisai" -ForegroundColor White
Write-Host "2. Tab Variables - pastikan env var ini ada (tambah jika kurang):" -ForegroundColor White
Write-Host "   - SUPABASE_URL" -ForegroundColor Gray
Write-Host "   - SUPABASE_KEY" -ForegroundColor Gray
Write-Host "   - GROQ_API_KEY" -ForegroundColor Gray
Write-Host "   - WA_API_KEY" -ForegroundColor Gray
Write-Host "   - WA_PROVIDER (default: fonnte)" -ForegroundColor Gray
Write-Host "3. Redeploy service (tab Deployments -> Redeploy)" -ForegroundColor White
Write-Host "4. Tunggu build selesai, lalu cek:" -ForegroundColor White
Write-Host "   https://kita-cuan-wa-bot-larisai.up.railway.app/health" -ForegroundColor Cyan
Write-Host "   Response harus status: ok dan missing_env: []." -ForegroundColor Gray

Pop-Location
