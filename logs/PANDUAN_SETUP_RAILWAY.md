# Panduan Setup Railway Service untuk Bot WhatsApp

Dokumen ini menjelaskan langkah-langkah untuk service Railway:

- `bukuwarung-ai-larisai` — Bot CS (BukuWarung-AI webhook) — **dari monorepo `bukuwarung-ai`**
- `kita-cuan-wa-bot-larisai` — Bot pencatatan WhatsApp — **dari repo TERPISAH [`157vis/kita-cuan-wa-bot`](https://github.com/157vis/kita-cuan-wa-bot)**

> Kedua service ini terpisah dari service `larisai.my.id` yang menjalankan Streamlit dashboard.

> **Migrasi 2026-07-03**: Bot `kita-cuan-wa-bot` sudah dipisah dari
> monorepo ke repo GitHub tersendiri. Ini menghindari Root Directory
> conflict di Nixpacks (parent folder tidak ter-deploy). Setup service
> Railway di repo baru — lihat Langkah di bawah.

---

## Status Saat Ini

| Service | URL | Repo | Status |
|---|---|---|---|
| **CS Webhook** | `bukuwarung-ai-larisai.up.railway.app` | `157vis/bukuwarung-ai` | Setup via monorepo (Root Directory = /) |
| **WA Catat** | `kita-cuan-wa-bot-larisai.up.railway.app` | `157vis/kita-cuan-wa-bot` (TERPISAH) | Setup via repo baru |
| **Streamlit** | `larisai.my.id` | `157vis/bukuwarung-ai` | ✅ Dashboard hidup |

---

## Service 1: bukuwarung-ai-larisai (CS Webhook)

### Langkah 1 — Buka Settings service

1. Login ke https://railway.app
2. Pilih project workspace
3. Klik service **`bukuwarung-ai-larisai`**
4. Klik tab **Settings** (ikon gear)

### Langkah 2A — Root Directory: **KOSONGKAN** (default `/`)

Cari bagian **"Source"** atau **"Build"**:

- **Root Directory**: **KOSONGKAN** (jangan isi sub-folder). Biarkan
  default Railway = repo root.

> **Kenapa?** Service `bukuwarung-ai` butuh import `laris_core`,
> `paths`, `brand` yang ada di **root repo** (`/app/...` di container).
> Kalau Root Directory = sub-folder, Railway/Nixpacks **hanya push
> sub-folder** ke container (`/app/bukuwarung-ai/`) dan parent
> (root repo) TIDAK ter-deploy → `ModuleNotFoundError: brand` /
> `laris_core` / `paths`. Setting Root Directory = `/` push seluruh
> repo, sehingga semua module di root bisa di-import.

### Langkah 3 — Start Command (**WAJIB ON toggle Custom Start Command**)

Bagian **"Deploy"** → **"Custom Start Command"**:

1. **Aktifkan toggle "Use Custom Start Command"** (harus ON / biru).
   > ⚠️ **PENTING — toggle "Use Custom BUILD Command" harus OFF!**
   > Kalau Build Command toggle ON, Railway auto-set `buildCommand`
   > dari `Procfile` (yang punya `web: python -m uvicorn ...`), dan
   > validator Railway akan reject kalau `startCommand` isinya sama.
   > Error: `buildCommand and startCommand cannot be the same`.
   > Pastikan **Build Command toggle = OFF** dan **Start Command
   > toggle = ON**.

2. Isi **Start Command** dengan:
   ```
   python -m uvicorn bukuwarung-ai.main:app --host 0.0.0.0 --port $PORT
   ```

3. **JANGAN isi Build Command** (toggle OFF → Railway pakai Nixpacks
   auto-detect: `pip install -r requirements.txt` di root).

> Root Directory kosong (default `/`) + Custom Start Command ON =
> SELURUH repo ter-deploy ke `/app/`, start command pakai module path
> lengkap. Aman dari `streamlit: command not found` dan
> `ModuleNotFoundError: brand/paths/laris_core`.

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

## Service 2: kita-cuan-wa-bot-larisai (WA Catat) — **REPO TERPISAH**

> ⚠️ **Migrasi 2026-07-03**: Bot ini sudah **dipisah** ke repo
> GitHub tersendiri: 👉 **https://github.com/157vis/kita-cuan-wa-bot**
>
> Alasan: monorepo `bukuwarung-ai` menyebabkan conflict di Railway
> (parent folder tidak ter-deploy kalau Root Directory = sub-folder).
> Repo baru `kita-cuan-wa-bot` sudah **self-contained** (`paths.py`,
> `brand.py`, `laris_core.py` semua di-copy ke repo baru).

### A. Buat service di Railway dari repo baru

1. Di project workspace Railway, klik **+ New Service**
2. Pilih **GitHub Repo** → **`157vis/kita-cuan-wa-bot`** (bukan `bukuwarung-ai`)
3. Setelah service dibuat, klik → tab **Settings**

### B. Settings

- **Service Name**: `kita-cuan-wa-bot-larisai`
- **Root Directory**: **KOSONGKAN** (default `/`). Repo ini self-contained,
  tidak butuh akses ke parent.
- **Custom Build Command**: toggle **OFF** (jangan ON!)
- **Custom Start Command**: **WAJIB ON toggle** (Custom Start Command toggle)
- **Start Command**:
  ```
  python -m uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
  (Module path TANPA prefix `kita-cuan-wa-bot.` karena repo ini adalah
  bot folder itu sendiri — `main.py` ada di root repo)
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
2. Cek log — kalau error `ModuleNotFoundError`, berarti ada masalah
   dependencies. Cek tab Variables.
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

### Runtime error: `/bin/bash: line 1: streamlit: command not found`
Artinya service menjalankan `streamlit run app.py` (dari `Procfile` /
`railway.toml` di root repo), tapi `streamlit` **tidak terinstall** di
environment service ini (karena `requirements.txt` di sub-folder
`tidak` memuat `streamlit`).

**Fix**:
1. Buka Settings service → Deploy
2. **Aktifkan toggle "Use Custom Start Command"** (wajib ON)
3. Isi start command yang benar:
   - bukuwarung-ai-larisai: `python -m uvicorn bukuwarung-ai.main:app --host 0.0.0.0 --port $PORT`
   - kita-cuan-wa-bot-larisai: `python -m uvicorn kita-cuan-wa-bot.main:app --host 0.0.0.0 --port $PORT`
4. Save & redeploy

### Runtime error: `ModuleNotFoundError: No module named 'brand'` / `'laris_core'` / `'paths'`
Artinya service jalan dengan `Root Directory = sub-folder` (mis.
`bukuwarung-ai/` atau `kita-cuan-wa-bot/`). Nixpacks/Railway **hanya
push sub-folder** ke container, sehingga `brand.py`, `laris_core.py`,
`paths.py` di root repo **TIDAK ada** di `/app/`.

**Fix**:
1. Buka Settings service → Source
2. **Kosongkan "Root Directory"** (default Railway = `/`, push seluruh repo)
3. **Aktifkan toggle "Use Custom Start Command"** (wajib ON)
4. Isi start command module path lengkap:
   - bukuwarung-ai-larisai: `python -m uvicorn bukuwarung-ai.main:app --host 0.0.0.0 --port $PORT`
   - kita-cuan-wa-bot-larisai: `python -m uvicorn kita-cuan-wa-bot.main:app --host 0.0.0.0 --port $PORT`
5. Save & redeploy

> **Konvensi** (sudah difix di `railway.toml`/`railway.json`/`Procfile`):
> - Root Directory = `/` → start command = `module.submodule:app`
>   (pakai module path lengkap karena cwd = `/app/`)
> - **JANGAN set Root Directory = sub-folder** untuk service ini
>   (parent folder tidak ter-deploy)

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
