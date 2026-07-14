# 🚨 Panduan: Buat Service Streamlit Dashboard di Railway

## ❗ Masalah

Tombol "Masuk" di landing page (yang sudah di-update ke `https://larisai.my.id`) malah buka JSON FastAPI, bukan halaman login Streamlit.

**Penyebab**: `larisai.my.id` adalah **FastAPI webhook** (bukan Streamlit). Streamlit dashboard tidak punya service yang running.

## 📊 Status Railway Services Saat Ini

| Service | Domain | App | Status |
|---|---|---|---|
| `bukuwarung-ai-larisai` | `bukuwarung-ai-larisai.up.railway.app` | FastAPI | ✅ Hidup |
| `kita-cuan-wa-bot-larisai` | `kita-cuan-wa-bot-larisai.up.railway.app` | FastAPI (WA Bot) | ✅ Hidup |
| **`streamlit-dashboard-larisai`** | **`app.larisai.my.id`** | **Streamlit** | ❌ **TIDAK ADA!** |

DNS `app.larisai.my.id` CNAME → `dc68nqvu.up.railway.app` (CNAME pointing), tapi service Railway sudah tidak ada.

## ✅ Solusi: Buat Service Streamlit Baru

### Step 1: Login Railway

1. Buka: https://railway.app
2. Login dengan GitHub
3. Pilih project **"heroic-stillness"** (atau nama project Railway Anda)

### Step 2: Create New Service

1. Klik **"+ New"** di kanan atas
2. Pilih **"GitHub Repo"**
3. Pilih repo: **`157vis/bukuwarung-ai`**
4. Klik **"Deploy"**

### Step 3: Konfigurasi Service Baru

1. Klik service baru (misal default `bukuwarung-ai` — rename jadi `streamlit-dashboard-larisai`)
2. Tab **"Settings"** (di sidebar kanan):

**Bagian "Service"**:
- **Service Name**: `streamlit-dashboard-larisai`
- **Root Directory**: `/` (root, BUKAN `bukuwarung-ai`)

**Bagian "Deploy"**:
- **Custom Start Command**: ON, isi: `python -m streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true`
- **Healthcheck Path**: `/_stcore/health`
- **Healthcheck Timeout**: 120
- **Restart Policy**: ON_FAILURE, max 5 retries

**Bagian "Build"** (scroll ke bawah):
- **Custom Build Command**: OFF (biarkan default Nixpacks)
- **Builder**: NIXPACKS

### Step 4: Set Environment Variables

1. Tab **"Variables"**
2. Tambahkan (sesuaikan dengan `.streamlit/secrets.toml.example`):
   - `SUPABASE_URL` = `https://xxx.supabase.co`
   - `SUPABASE_KEY` = `eyJhbGc...`
   - `BUKUWARUNG_BASE_URL` = `https://bukuwarung-ai-larisai.up.railway.app`
   - `RAILWAY_URL` = `https://bukuwarung-ai-larisai.up.railway.app`
   - Variable lain sesuai `app.py` & `login.py`

3. Klik **"Add"** untuk setiap variable

### Step 5: Tunggu Build & Deploy

1. Railway otomatis trigger build
2. Tunggu 3-5 menit sampai deployment sukses
3. Cek logs: harusnya `Streamlit started at port $PORT`

### Step 6: Generate Domain (jika perlu)

1. Tab **"Settings"** → **"Domains"**
2. Klik **"Generate Domain"** → dapat URL Railway: `https://streamlit-dashboard-larisai.up.railway.app`
3. Test: buka URL di browser → harusnya muncul halaman login Streamlit

### Step 7: Link Custom Domain `app.larisai.my.id`

1. Tab **"Settings"** → **"Domains"**
2. Klik **"Custom Domain"**
3. Masukkan: `app.larisai.my.id`
4. Klik **"Add"**

Railway akan otomatis:
- Verifikasi DNS record (yang sudah ada: `app.larisai.my.id` CNAME → `dc68nqvu.up.railway.app`)
- Setup SSL/TLS
- Generate CNAME baru untuk service ini

5. **PENTING**: Update DNS record `app.larisai.my.id` di Cloudflare:
   - Buka Cloudflare DNS Records
   - Edit record `app` CNAME
   - Ganti Content dari `dc68nqvu.up.railway.app` ke URL baru yang Railway kasih (lihat notifikasi "Add the following records" di dashboard)
   - Save

### Step 8: Verifikasi

Buka browser Incognito: https://app.larisai.my.id/

Harusnya muncul **halaman login Streamlit**, bukan JSON atau 404.

## ⏱️ Estimasi Waktu

- Step 1-3 (Buat service): 3 menit
- Step 4 (Env vars): 3 menit
- Step 5 (Build): 5 menit
- Step 6 (Domain Railway): 1 menit
- Step 7-8 (Custom domain + verifikasi): 5 menit

**Total: ~15-20 menit**

## 🆘 Troubleshooting

### "Port already in use"

Jika error port conflict, kemungkinan env var `PORT` tidak ter-set. Railway otomatis set, tapi cek di tab Variables.

### "ModuleNotFoundError: No module named 'streamlit'"

1. Pastikan `requirements.txt` di root repo ada `streamlit`
2. Cek di Tab **"Build Logs"** apakah Nixpacks install semua dependencies

### "streamlit: command not found"

Gunakan custom start command:
```
python -m streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

### DNS CNAME conflict

Jika muncul error "CNAME already exists" di Railway:

1. Railway kasih URL baru: mis. `abcdef.up.railway.app`
2. Update Cloudflare DNS `app.larisai.my.id`:
   - CNAME → `abcdef.up.railway.app` (URL baru dari Railway, BUKAN `dc68nqvu.up.railway.app` lama)
3. Tunggu propagasi 5-10 menit

## 💡 Alternative: Pakai Sub-domain Lain

Jika `app.larisai.my.id` susah di-link, gunakan sub-domain lain:
- `dashboard.larisai.my.id`
- `panel.larisai.my.id`
- `streamlit.larisai.my.id`

Setup:
1. Cloudflare DNS → Add record:
   - Type: CNAME
   - Name: `dashboard` (atau nama lain)
   - Content: URL Railway yang di-generate
   - Proxy: DNS only (untuk hindari konflik)
2. Railway → Settings → Custom domain → masukkan `dashboard.larisai.my.id`

## 💡 Update Landing Page CTA (Sementara)

Sambil menunggu Streamlit service ready, update CTA di `pages-deploy/index.html` ke:
- `https://wa.me/6282112826851?text=Halo%20laris.AI%2C%20saya%20mau%20akses%20dashboard` (WhatsApp)

Atau biarkan `https://larisai.my.id` (FastAPI) — yang muncul JSON tapi minimal bisa diklik, nanti kita update lagi setelah Streamlit service siap.
