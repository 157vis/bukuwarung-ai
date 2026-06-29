# Deploy BukuWarung-AI ke Railway

Panduan deploy bot multi-agent WhatsApp ke [Railway](https://railway.app).

## Prasyarat

- Akun Railway (login GitHub)
- Repo `157vis/bukuwarung-ai` (atau fork Anda)
- API keys: OpenRouter, Supabase, Fonnte, Groq
- SQL dijalankan di Supabase: `sql/create_otak_memories.sql`, `sql/create_brand_voices.sql`

## Langkah deploy

### 1. Buat project Railway

1. **New Project** → **Deploy from GitHub repo**
2. Pilih repo → set **Root Directory** = `bukuwarung-ai` (jika monorepo)
3. Railway mendeteksi `Procfile` / `railway.json` otomatis

### 2. Environment variables

Di Railway → **Variables**, tambahkan semua dari `.env.example`:

| Variable | Wajib | Keterangan |
|----------|-------|------------|
| `OPENROUTER_API_KEY` | ✅ | Chat LLM |
| `SUPABASE_URL` | ✅ | Database |
| `SUPABASE_KEY` | ✅ | Service role atau anon |
| `FONNTE_TOKEN` | ✅ | Token device Fonnte |
| `GROQ_API_KEY` | ✅ | Embedding memory |
| `PRIMARY_MODEL` | | Default: minimax/minimax-m3 |
| `BACKUP_MODEL` | | Fallback saat rate limit |
| `FREE_MODEL` | | Fallback gratis |
| `OWNER_PHONES` | | Nomor owner untuk AdminAgent |
| `APP_NAME` | | Nama tenant default |
| `PORT` | | Di-set Railway otomatis |

Railway menyuntikkan `PORT` — **jangan** hardcode di kode.

### 3. Domain & health check

1. **Settings** → **Networking** → **Generate Domain**
2. Health check: `GET https://<domain>/health` → `{"status":"ok",...}`
3. `railway.json` sudah mengarah ke `/health`

### 4. Connect Fonnte

1. Login [fonnte.com](https://fonnte.com) → device WhatsApp
2. **Webhook URL**: `https://<railway-domain>/webhook-whatsapp`
3. Method: **POST**
4. Test kirim pesan WA → cek log Railway

### 5. Verifikasi post-deploy

```bash
curl https://<domain>/health
curl https://<domain>/stats
```

Kirim WA: `halo` → harus dapat balasan otomatis.

## Multi-client (banyak toko)

Satu Railway → banyak UMKM. Lihat **[docs/MULTI_CLIENT_SETUP.md](docs/MULTI_CLIENT_SETUP.md)**.

Ringkas:
1. Jalankan `sql/create_clients.sql`
2. Insert row per toko di tabel `clients`
3. Fonnte webhook: `/webhook-whatsapp/toko_berkah`
4. Cek: `GET /clients`

## Pre-deploy checklist

Lihat `docs/PRE_DEPLOY_CHECKLIST.md`.

## Troubleshooting Railway

| Masalah | Solusi |
|---------|--------|
| Build gagal | Cek `runtime.txt` Python 3.11, `requirements.txt` valid |
| 502 Bad Gateway | Pastikan start command `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health check fail | Buka `/health` — pastikan app boot tanpa crash |
| WA tidak balas | Cek `FONNTE_TOKEN`, webhook URL, log `webhook in` |
| LLM error | Cek `OPENROUTER_API_KEY`, model name valid |
| Memory kosong | Jalankan SQL Supabase, cek `GROQ_API_KEY` |

## Rollback

Railway → **Deployments** → pilih deploy sebelumnya → **Redeploy**.

## Tag release

```bash
git tag v1.0.0
git push origin v1.0.0
```
