# Panduan Setup Railway Service untuk Bot WhatsApp

Dokumen ini menjelaskan langkah-langkah untuk menambahkan/memperbaiki 2 service Railway
yang menjalankan bot WhatsApp CS (`bukuwarung-ai-larisai`) dan bot pencatatan
(`kita-cuan-wa-bot-larisai`).

> Kedua service ini terpisah dari service `larisai.my.id` yang menjalankan Streamlit dashboard.

---

## Status Saat Ini

| Service | URL | Status | Realita |
|---|---|---|---|
| **CS Webhook** | `bukuwarung-ai-larisai.up.railway.app` | 200 (tapi Streamlit) | ❌ Root Dir salah — menjalankan Streamlit |
| **WA Catat** | `kita-cuan-wa-bot-larisai.up.railway.app` | 404 | ❌ Service tidak jalan |
| **Streamlit** | `larisai.my.id` | 200 (benar) | ✅ Dashboard hidup |

---

## Service 1: bukuwarung-ai-larisai (CS Webhook)

### Langkah 1 — Buka Settings service

1. Login ke https://railway.app
2. Pilih project workspace
3. Klik service **`bukuwarung-ai-larisai`**
4. Klik tab **Settings** (ikon gear)

### Langkah 2 — Perbaiki Root Directory

Cari bagian **"Source"** atau **"Build"**:

- **Root Directory**: ubah dari `/` (kosong) menjadi `bukuwarung-ai`
- **Watch Paths**: opsional, kosongkan

> Ini memberitahu Railway bahwa source code untuk service ini ada di folder `bukuwarung-ai/`,
> bukan di root repo.

### Langkah 3 — Start Command

Bagian **"Deploy"** → **"Custom Start Command"**:

```
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

> Klik toggle **"Use Custom Start Command"** agar override Procfile/railway.json.

### Langkah 4 — Environment Variables

Tab **Variables** → klik **+ New Variable**, tambahkan satu per satu:

| Name | Value | Keterangan |
|---|---|---|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | Dari Supabase Dashboard → Settings → API |
| `SUPABASE_ANON_KEY` | `eyJ...` | Anon public key (Supabase) |
| `SUPABASE_SERVICE_KEY` | `eyJ...` | **Service role** key (JANGAN share) |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | https://openrouter.ai/keys |
| `SECRET_KEY` | string random panjang | Mis. `laris-ai-2026-r4nd0m-string` |
| `RAILWAY_URL` | `https://bukuwarung-ai-larisai.up.railway.app` | URL service ini |
| `FONNTE_TOKEN` | token dari fonnte.com | Optional, tapi biasanya dipakai untuk CS |

Tambahan (opsional):
- `PRIMARY_MODEL` → default `minimax/minimax-m3`
- `BACKUP_MODEL` → default `deepseek/deepseek-chat-v3`
- `FREE_MODEL` → default `qwen/qwen3-coder:free`
- `DEBUG` → set `true` untuk debug

### Langkah 5 — Trigger Deploy

1. Tab **Deployments**
2. Klik **"Redeploy"** atau **"Deploy"**
3. Tunggu build selesai (cek log)
4. Test: buka `https://bukuwarung-ai-larisai.up.railway.app/health` — harus return JSON, BUKAN HTML Streamlit

Expected response (contoh):
```json
{
  "status": "BukuWarung-AI is running",
  "version": "1.0.1",
  "model": "minimax/minimax-m3"
}
```

---

## Service 2: kita-cuan-wa-bot-larisai (WA Catat)

> **Penting**: Service ini mungkin BELUM dibuat di Railway. Kalau tidak ada,
> Anda perlu create new service dari GitHub repo yang sama.

### A. Kalau Service Belum Ada

1. Di project workspace Railway, klik **+ New Service**
2. Pilih **GitHub Repo** → `157vis/bukuwarung-ai`
3. Setelah service dibuat, klik → tab **Settings**

### B. Settings

- **Service Name**: `kita-cuan-wa-bot-larisai`
- **Root Directory**: `kita-cuan-wa-bot`  ← **WAJIB, kalau tidak akan error build**
- **Custom Start Command**:
  ```
  python -m uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
- **Healthcheck Path**: `/`

### C. Variables

| Name | Value | Keterangan |
|---|---|---|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | URL Supabase project |
| `SUPABASE_KEY` | `eyJ...` (service role) | **Service role** key |
| `GROQ_API_KEY` | `gsk_...` | https://console.groq.com/keys |
| `WA_API_KEY` | token dari Fonnte | https://md.fonnte.com |
| `WA_PROVIDER` | `fonnte` | Default: fonnte |
| `STOCK_THRESHOLD` | `10` | Batas minimum stok |
| `REORDER_QTY` | `20` | Jumlah restock default |

### D. Trigger Deploy & Test

1. **Deployments** → **Redeploy**
2. Cek log — kalau error `ModuleNotFoundError: paths`, berarti Root Directory salah
3. Test: `https://kita-cuan-wa-bot-larisai.up.railway.app/`

Expected response (contoh):
```json
{
  "status": "laris.AI WA Bot is running",
  "bot_name": "Laris",
  "provider": "fonnte",
  "wa_key_set": true,
  "supabase_set": true,
  "groq_set": true,
  "webhook": "/webhook"
}
```

---

## Troubleshoot

### Build failed: exit code 127 (pip not found)
Sudah difix di commit `8a68a2e`. Trigger redeploy.

### Service running tapi `/health` return 404
- Cek **Root Directory** di Settings — harus sesuai dengan folder source code.
- Cek **Custom Start Command** — harus pakai `python -m uvicorn main:app ...`

### Service running tapi `wa_key_set: false`
- Cek tab **Variables** → `WA_API_KEY` harus ada dan tidak kosong

### Service running tapi tidak bisa kirim WA
- Cek token Fonnte masih aktif di https://md.fonnte.com
- Cek nomor pengirim WA sudah connected
- Cek webhook URL di dashboard Fonnte = `https://kita-cuan-wa-bot-larisai.up.railway.app/webhook`

### Orchestrator tidak instantiate
- Service bukuwarung-ai butuh `OPENROUTER_API_KEY`
- Cek log: kalau ada error `OpenRouter API key not set`, tambahkan env var

---

## Verifikasi Akhir

Setelah kedua service running:

```bash
# CS Webhook
curl https://bukuwarung-ai-larisai.up.railway.app/health
# → JSON status

# WA Catat
curl https://kita-cuan-wa-bot-larisai.up.railway.app/
# → JSON dengan wa_key_set:true

# Kirim test POST ke webhook CS
curl -X POST https://bukuwarung-ai-larisai.up.railway.app/webhook-whatsapp \
  -H "Content-Type: application/json" \
  -d '{"device":"test","sender":"628112345678","message":"halo"}'
# → JSON (bukan 404/405)

# Kirim test POST ke webhook catat
curl -X POST https://kita-cuan-wa-bot-larisai.up.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"device":"test","sender":"628112345678","message":"jual kopi 50000"}'
# → JSON status:ok
```

Kalau ada error, copy paste log dari tab **Logs** service yang gagal.
