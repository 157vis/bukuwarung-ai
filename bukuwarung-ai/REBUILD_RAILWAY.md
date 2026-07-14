# PANDUAN REBUILD SERVICE `bukuwarung-ai-larisai` DI RAILWAY

## Kenapa perlu rebuild?

Service `bukuwarung-ai-larisai` saat ini menjalankan **Streamlit dashboard**,
bukan FastAPI webhook. Setiap endpoint (`/health`, `/clients`, `/webhook/...`)
mengembalikan HTML Streamlit alih-alih JSON.

| URL | Response | Diagnosa |
|---|---|---|
| `/health` | Streamlit HTML | ❌ Bukan FastAPI |
| `/clients` | Streamlit HTML | ❌ |
| `/webhook/...` | Streamlit HTML | ❌ |
| `/_stcore/health` | `ok` | ✅ Streamlit healthcheck |

Akar masalah: di Railway dashboard, **Custom Start Command** service ini
ter-override ke `python -m streamlit run app.py` (sama dengan root
`railway.toml` Streamlit dashboard).

---

## LANGKAH REBUILD

### STEP 1 — Backup konfigurasi lama (SEBELUM hapus)

1. Login https://railway.app
2. Pilih project **larisai** (atau nama project Anda)
3. Klik service **`bukuwarung-ai-larisai`**
4. **Tab Variables** — copy semua variabel env (klik ikon mata, atau screenshot):
   ```
   OPENROUTER_API_KEY = <value>
   SUPABASE_URL = <value>
   SUPABASE_SERVICE_KEY = <value>
   GROQ_API_KEY = <value>
   SUPABASE_KEY = <value>          (opsional, alias)
   SECRET_KEY = <value>            (opsional)
   PRIMARY_MODEL = minimax/minimax-m3   (opsional)
   BACKUP_MODEL = deepseek/deepseek-chat-v3
   FREE_MODEL = qwen/qwen3-coder:free
   ```
5. **Tab Settings** — catat:
   - **Custom Start Command** (kalau ada)
   - **Root Directory** (kalau ada)
   - **Custom Build Command** (kalau ada)
   - **Healthcheck Path** (kalau ada)
6. Simpan catatan ini ke notepad / kertas.

### STEP 2 — Hapus service lama

1. Klik service **`bukuwarung-ai-larisai`**
2. **Tab Settings** → scroll ke bawah
3. Klik **Delete Service** (tombol merah di bagian bawah)
4. Konfirmasi delete
5. Tunggu 30 detik sampai service hilang dari sidebar

### STEP 3 — Buat service baru

1. Di project yang sama, klik **+ New Service** (tombol hijau, kanan atas)
2. Pilih **GitHub Repo**
3. Pilih repo **`157vis/bukuwarung-ai`** (monorepo bukuwarungai)
4. **PENTING — setting awal**:
   - **Branch**: `main`
   - **Root Directory**: `bukuwarung-ai` ← HARUS di-set!
   - **Service Name**: `bukuwarung-ai-larisai` (atau nama lain sesuai preferensi)

### STEP 4 — Konfigurasi Build & Start

Buka service baru → tab **Settings**:

| Field | Value | Keterangan |
|---|---|---|
| **Root Directory** | `bukuwarung-ai` | Subfolder berisi FastAPI |
| **Custom Build Command** | (kosong / OFF) | Biarkan Nixpacks auto-detect |
| **Custom Start Command** | `python -m uvicorn bukuwarung-ai.main:app --host 0.0.0.0 --port $PORT` | **WAJIB ON** |

Kalau toggle Custom Start Command OFF, isi di field teks yang muncul.
Pastikan toggle **Custom Build Command** tetap OFF (Nixpacks auto-detect).

### STEP 5 — Tambah Environment Variables

Tab **Variables** → klik **+ New Variable** untuk setiap:

| Name | Value | Wajib? |
|---|---|---|
| `OPENROUTER_API_KEY` | `<value-dari-step-1>` | ✅ WAJIB |
| `SUPABASE_URL` | `<value-dari-step-1>` | ✅ WAJIB |
| `SUPABASE_SERVICE_KEY` | `<value-dari-step-1>` | ✅ WAJIB |
| `GROQ_API_KEY` | `<value-dari-step-1>` | ✅ WAJIB |
| `SECRET_KEY` | `<value-dari-step-1>` | ⚠️ Disarankan (untuk signing) |
| `PRIMARY_MODEL` | `minimax/minimax-m3` | ⚠️ Opsional |
| `BACKUP_MODEL` | `deepseek/deepseek-chat-v3` | ⚠️ Opsional |
| `FREE_MODEL` | `qwen/qwen3-coder:free` | ⚠️ Opsional |

### STEP 6 — Tunggu Build & Deploy

1. Service baru auto-deploy (atau klik **Deploy** di tab Deployments)
2. Build dengan Nixpacks biasanya 3-5 menit (V3)
3. Cek tab **Logs** — harus ada baris:
   ```
   INFO:     Started server process [xxx]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8080
   ```

### STEP 7 — Verify

Test endpoint dari PowerShell / browser:

```bash
# 1. Health
curl https://bukuwarung-ai-larisai.up.railway.app/health
# Expected: JSON {"status":"ok","app":"BukuWarung-AI",...}

# 2. Root
curl https://bukuwarung-ai-larisai.up.railway.app/
# Expected: JSON {"name":"BukuWarung-AI","version":"1.0.1",...}

# 3. Stats
curl https://bukuwarung-ai-larisai.up.railway.app/stats
# Expected: JSON stats

# 4. Clients
curl https://bukuwarung-ai-larisai.up.railway.app/clients
# Expected: JSON list clients
```

Kalau semua return **JSON** (bukan HTML), service sudah benar.

### STEP 8 — Sambungkan Domain

Tab **Settings** → **Domains** → **+ Add Domain**:

1. Tambah domain Railway-generated: `bukuwarung-ai-larisai.up.railway.app`
2. Klik **Generate Domain** (Railway akan buat otomatis)
3. Tunggu ~30 detik sampai DNS propagate
4. Test: `curl https://bukuwarung-ai-larisai.up.railway.app/health`

---

## CHECKLIST SEBELUM LANJUT KE STEP 2

- [ ] Env var lama sudah di-screenshot / di-copy ke notepad
- [ ] Backup database: kalau pakai Supabase tier gratis, biasanya tidak perlu backup
- [ ] Service `kita-cuan-wa-bot-larisai` TIDAK boleh dihapus (yang lain dipakai WA bot)
- [ ] Streamlit dashboard `larisai.my.id` TIDAK boleh dihapus

## TROUBLESHOOTING SETELAH REBUILD

### `/health` masih return HTML Streamlit

Artinya: Root Directory atau Start Command masih salah.
- Tab **Settings** → **Root Directory** = `bukuwarung-ai`
- Tab **Settings** → **Custom Start Command** = `python -m uvicorn bukuwarung-ai.main:app --host 0.0.0.0 --port $PORT`
- Tab **Deployments** → **Redeploy**

### `/health` return 502 / 503

- Tab **Logs** → cek error
- Biasanya env var kurang
- Buka `https://bukuwarung-ai-larisai.up.railway.app/health`, field `missing_env` di JSON akan list yang kurang

### Build gagal

- Tab **Logs** → lihat error Nixpacks
- Kemungkinan: requirements.txt conflict, atau `Root Directory` salah
- Cek `bukuwarung-ai/requirements.txt` — pastikan ada `fastapi`, `uvicorn[standard]`, `pydantic`, `supabase`, `groq`, `httpx`, `python-dotenv`, `openrouter`, dll

### Port issue

Railway otomatis inject `$PORT`. Start command harus pakai `$PORT`:
```
python -m uvicorn bukuwarung-ai.main:app --host 0.0.0.0 --port $PORT
```
JANGAN hardcode port 8000 (Railway akan random assign).

---

## SETELAH REBUILD BERHASIL

Jalankan E2E test untuk pastikan link `larisai.my.id` → bot → webhook CS:

```bash
# 1. Cek streamlit dashboard bisa tambah client
# Login larisai.my.id → Super Admin → Tambah Client Baru
# Seharusnya tidak error (sebelumnya return HTML)

# 2. Cek WA bot masih jalan
curl https://kita-cuan-wa-bot-larisai.up.railway.app/health
# Expected: {"status":"ok","missing_env":[]}

# 3. Cek webhook CS bisa di-call dari dashboard
# Dashboard panggil: BUKUWARUNG_BASE_URL + "/clients"
# Seharusnya return JSON list, bukan HTML

# 4. Cek webhook Fonnte bisa di-set per client
# Dashboard panggil: BUKUWARUNG_BASE_URL + "/clients/{user_id}/webhook/fonnte"
# Seharusnya return URL webhook siap untuk di-paste ke Fonnte
```

Kalau semua ✅, ekosistem laris.AI UMKM sudah fully operational.
