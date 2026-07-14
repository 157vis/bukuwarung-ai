# 🔧 Panduan Fix Manual — Service `bukuwarung-ai` di Railway

> **Tujuan**: Agar `bukuwarung-ai-larisai.up.railway.app` & `larisai.my.id` menjalankan **FastAPI** (bukan Streamlit lagi), sehingga AI agent CS UMKM (`/webhook`, `/chat`, `/health`) bisa aktif.

---

## 📋 Diagnosa (sudah selesai)

Service **`bukuwarung-ai`** (UUID `8e5069a2-9fa4-4452-be8d-cd45acdc7872`) ada di environment **`production`** dari project `heroic-stillness`.

**Konfigurasi saat ini** (SALAH):

| Setting | Value saat ini | Seharusnya |
|---|---|---|
| Source Repo | `157vis/bukuwarung-ai` | ✅ Sudah benar |
| Branch | `main` | ✅ Sudah benar |
| **Root Directory** | `bukuwarung-ai` | ✅ **Sudah benar** (mengarah ke subfolder `bukuwarung-ai/` di monorepo) |
| **Custom Start Command** | `python -m streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true` | ❌ `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Healthcheck Path** | `/_stcore/health` | ❌ `/health` |
| **Region (Scale)** | `sfo` (INVALID) | ❌ Pilih region valid, misal `us-west` |

**Domain yang ter-link** (tidak perlu diubah):
- `bukuwarung-ai-larisai.up.railway.app` (Railway default)
- `larisai.my.id` (Cloudflare custom)

---

## 🚀 Langkah Fix Manual (5 langkah)

### Step 1: Buka Service Settings

Tab browser Railway masih terbuka di:
```
https://railway.com/project/acb82dc5-efaa-4daf-98c5-de22e5074a29/service/8e5069a2-9fa4-4452-be8d-cd45acdc7872/settings
```

Jika tidak, klik **Dashboard → heroic-stillness → bukuwarung-ai → tab Settings** (di sidebar kanan).

---

### Step 2: Fix Region `sfo` → Pilih Region Valid

1. **Scroll ke bagian "Scale"** (heading: "Deploy replicas per region for horizontal scaling.")
2. Anda akan melihat **banner merah/kuning**:
   > Invalid region `sfo` is configured on this service and is blocking deployments. Pick a replacement region below — your workspace's default is pre-selected.
3. **Slider/select "Replicas"** ada 2 kontrol (region 1 dan region 2).
4. **Region 1 (slider 2)**: biarkan atau pilih default workspace (kemungkinan `us-west`).
5. **Region 2 (slider 1)**: kemungkinan di-set ke `sfo` — **UBAH ke region valid** atau set replicas = 0.
6. Klik **Update** / tunggu auto-save.

**Region yang valid di Railway** (2026):
- `us-west` (US West — paling umum)
- `us-east` (US East)
- `eu-west` (Europe West)
- `ap-southeast` (Asia Pacific)

**Cara paling aman**: Pilih `us-west` di kedua region slider (pakai default workspace).

---

### Step 3: Fix Custom Start Command → FastAPI

> ⚠️ **PENTING**: Sebelum step ini, lihat **Troubleshooting → "Build manifest could not be parsed"** di bawah. `railway.toml` di root repo konflik dan harus di-fix **DULU** (atau override via "Railway Config File").

1. **Scroll ke bagian "Deploy"** (heading: "Command that will be run to start new deployments.")
2. Anda akan melihat **Start command** field (saat ini readonly dengan nilai Streamlit — atau mungkin `uvicorn bukuwarung-ai.main:app` yang SALAH).
3. **Look for toggle "Override"** atau "Use Custom Start Command" — **enable** jika belum.
4. **Klik field Start command** dan **ganti** seluruh isinya menjadi:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. **Tekan Tab/Enter** atau klik di luar field untuk simpan.

> **Catatan penting**: 
> - **JANGAN** pakai `uvicorn bukuwarung-ai.main:app` — itu yang menyebabkan error `ModuleNotFoundError: No module named 'bukuwarung-ai'` (lihat log error).
> - Karena **Root Directory = `bukuwarung-ai`** sudah menunjuk ke subfolder yang berisi `main.py`, cukup `main:app` saja.
> - Field ini mungkin awalnya `readonly` sampai Anda enable toggle-nya. Cari switch/toggle di samping label "Custom Start Command" atau "Override".

---

### Step 4: Fix Healthcheck Path → `/health`

1. Masih di bagian "Deploy", scroll sedikit ke bawah.
2. Cari **"Healthcheck Path"** (saat ini `/_stcore/health`).
3. Sama seperti Step 3, cari toggle "Override" jika field readonly.
4. **Ganti value** menjadi:
   ```
   /health
   ```
5. Save.

---

### Step 5: Trigger Redeploy

Setelah 3 perubahan di atas di-save:

1. Klik tab **"Deployments"** (di sidebar service, di atas tab Settings).
2. Di paling atas ada deployment terbaru dengan status **"BUILDING"** atau **"FAILED"**.
3. Klik tombol **"Redeploy"** (ikon refresh) di samping deployment.
4. Tunggu build (~2-5 menit).
5. Status harusnya jadi **"Deployment successful"** (centang hijau).

---

## ✅ Verifikasi

### Test 1: Cek endpoint `/health`

Buka di browser atau pakai curl:
```bash
curl https://bukuwarung-ai-larisai.up.railway.app/health
```

**Expected response (JSON, BUKAN HTML)**:
```json
{
  "status": "ok",
  "app": "BukuWarung-AI",
  "version": "1.0.1",
  "uptime_seconds": 123,
  "timestamp": "2026-07-07T07:15:00Z",
  "health": "/health"
}
```

### Test 2: Cek custom domain `larisai.my.id`

```bash
curl https://larisai.my.id/health
```

Harusnya return JSON yang sama (kalau `larisai.my.id` CNAME/proxy ke Railway).

### Test 3: Cek webhook endpoint

```bash
curl -X POST https://bukuwarung-ai-larisai.up.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"device":"test","message":"halo"}'
```

Expected: JSON response (bukan HTML 404 atau error).

---

## 🚨 Troubleshooting

### Kalau Start Command masih readonly
- Pastikan toggle "Override" di-enable
- Coba refresh halaman (F5) lalu ulangi

### Kalau masih "Deployment failed"
- Buka tab **"Logs"** (sidebar service)
- Lihat error terakhir di section "Build" atau "Deploy"
- Error umum:
  - `ModuleNotFoundError`: tambah library di `requirements.txt` di repo
  - `Port already in use`: tidak mungkin di Railway
  - `Healthcheck failed`: biasanya karena start command salah atau app crash saat startup

### ⚠️ "Build manifest could not be parsed" — `railway.toml` KONFLIK

**Ini masalah utama Anda.** Repo `157vis/bukuwarung-ai` commit `65a249d` punya `railway.toml` di **ROOT** yang isinya **Streamlit command**, BUKAN FastAPI:

```toml
# railway.toml di root repo (YANG SALAH):
startCommand = "python -m streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true"
healthcheckPath = "/_stcore/health"
```

**Root Directory = `bukuwarung-ai`** artinya Railway baca dari **subfolder `bukuwarung-ai/`**, TAPI `railway.toml` di **parent** (root) masih ter-baca duluan oleh Nixpacks.

**Solusi (PILIH SALAH SATU):**

#### Solusi A: Tambah `railway.toml` di subfolder (RECOMMENDED)

Saya sudah siapkan file-nya. **Jalankan di PowerShell**:

```powershell
# Pastikan subfolder ada
$bukuwarungAi = "C:\Users\Teknik SAP MTAL\bukuwarungai\bukuwarung-ai"
if (-not (Test-Path $bukuwarungAi)) {
  New-Item -ItemType Directory -Path $bukuwarungAi -Force
}

# Tulis railway.toml uvicorn (override parent Streamlit config)
@'
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port `$PORT"
healthcheckPath = "/health"
healthcheckTimeout = 120
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 5
'@ | Set-Content -Path "$bukuwarungAi\railway.toml" -Encoding UTF8

# PENTING: Start Command "uvicorn main:app" BUKAN "uvicorn bukuwarung-ai.main:app"
# Karena Root Directory = "bukuwarung-ai" sudah mengarah ke subfolder
# yang berisi main.py FastAPI

# Commit & push ke repo GitHub 157vis/bukuwarung-ai
cd $bukuwarungAi
git add railway.toml
git commit -m "fix: override parent railway.toml to use FastAPI uvicorn"
git push origin main
```

#### Solusi B: Hapus `railway.toml` dari root repo

Edit file di `C:\Users\Teknik SAP MTAL\bukuwarungai\railway.toml` (root monorepo):
- Ganti isinya jadi kosong, atau rename jadi `railway.toml.bak`
- Commit & push ke GitHub repo `157vis/bukuwarung-ai`

#### Solusi C: Override di UI Railway (PALING CEPAT, tanpa git push)

1. Di tab **Settings** service, scroll ke **"Config-as-code"** → **"Railway Config File"**
2. Klik **"Add File Path"** dan tambahkan entry:
   - File path: `railway.json`
3. Save. Railway akan prioritaskan `railway.json` (yang ada di subfolder, **SUDAH BENAR** isinya uvicorn + /health).
4. Railway Config File path jadi: `railway.json`

**Solusi C tidak butuh git push sama sekali** — Railway baca file dari subfolder via Root Directory.

---

## 📝 Ringkasan Perubahan

```
Region:    sfo         → us-west (atau default)
Start Cmd: streamlit   → uvicorn main:app --host 0.0.0.0 --port $PORT
Health:    /_stcore/health → /health
```

Setelah 3 perubahan itu, service harusnya deploy sukses dan FastAPI jalan.

**Tidak perlu rebuild service dari awal.** Service-nya sudah benar, cuma 3 setting yang salah.

---

## 🔗 URL Penting

- **Service Settings**: https://railway.com/project/acb82dc5-efaa-4daf-98c5-de22e5074a29/service/8e5069a2-9fa4-4452-be8d-cd45acdc7872/settings
- **Service Deployments**: https://railway.com/project/acb82dc5-efaa-4daf-98c5-de22e5074a29/service/8e5069a2-9fa4-4452-be8d-cd45acdc7872
- **Repo GitHub**: https://github.com/157vis/bukuwarung-ai/tree/main/bukuwarung-ai
- **Endpoint health**: https://bukuwarung-ai-larisai.up.railway.app/health
- **Endpoint custom domain**: https://larisai.my.id/health
