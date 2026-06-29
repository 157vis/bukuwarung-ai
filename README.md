# laris.AI — Buku Kas UMKM + Bot WhatsApp

Dashboard **Streamlit** + **bot WhatsApp** (Fonnte) dengan multi-agent AI: Admin, Logistik, Advisor.

| Komponen | Folder / file | Deploy |
|----------|---------------|--------|
| Dashboard | `app.py`, `login.py`, `laris_core.py` | Railway Streamlit atau `streamlit run app.py` |
| Bot WA | `kita-cuan-wa-bot/` | Railway → `https://bukuwarung-ai-larisai.up.railway.app` |
| Database | Supabase | Cloud (bukan di repo) |
| Landing SEO | `site/` | Static hosting (opsional) |

**Repo GitHub:** [github.com/157vis/bukuwarung-ai](https://github.com/157vis/bukuwarung-ai) — branch `main`

---

## Clone di laptop (baru)

```bash
git clone https://github.com/157vis/bukuwarung-ai.git
cd bukuwarung-ai
```

Panduan lengkap: **[docs/PANDUAN_SETUP_LAPTOP.md](docs/PANDUAN_SETUP_LAPTOP.md)**

Ringkas:

1. `python -m venv .venv` → aktifkan venv → `pip install -r requirements.txt`
2. Salin `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` (isi Supabase anon + Groq)
3. Salin `kita-cuan-wa-bot/.env.example` → `kita-cuan-wa-bot/.env` (isi service_role + WA + Groq)
4. Jalankan dashboard: `streamlit run app.py`
5. Jalankan bot (opsional lokal):
   ```bash
   cd kita-cuan-wa-bot
   uvicorn main:app --reload
   ```
   File bot **hanya satu:** `kita-cuan-wa-bot/main.py`

> File rahasia (`.env`, `secrets.toml`) **tidak** di-upload ke GitHub. Setiap laptop perlu salin dari contoh + isi key sendiri.

### Portable (flashdisk / HDD)

```powershell
pip install -r requirements.txt
.\scripts\run-dashboard.ps1
.\scripts\run-bot.ps1
```

Modul `paths.py` mengatur path relatif — tidak ada hardcode drive letter.

---

## SQL Supabase (sekali)

Jalankan di **Supabase → SQL Editor**:

1. `setup_laris_ai.sql` — tabel utama + approvals + wa_users
2. `sql/seed_trial_products.sql` — katalog stok trial
3. `sql/setup_client_rafiharliansyah34.sql` — client trial (sesuaikan email)

---

## Dokumentasi

| File | Isi |
|------|-----|
| [docs/PANDUAN_SETUP_LAPTOP.md](docs/PANDUAN_SETUP_LAPTOP.md) | Kerja dari laptop, sync git |
| [docs/PANDUAN_TRIAL_WA.md](docs/PANDUAN_TRIAL_WA.md) | Fonnte webhook + tes WA |
| [docs/PANDUAN_RAILWAY.md](docs/PANDUAN_RAILWAY.md) | Deploy Railway |
| [docs/PANDUAN_TAMBAH_CLIENT.md](docs/PANDUAN_TAMBAH_CLIENT.md) | Tambah client baru |
| [kita-cuan-wa-bot/README.md](kita-cuan-wa-bot/README.md) | Detail bot WA |

---

## Workflow harian (dua perangkat)

```bash
# Sebelum mulai kerja (pull perubahan terbaru)
git pull origin main

# Setelah selesai edit
git add .
git commit -m "Deskripsi singkat perubahan"
git push origin main
```

Railway otomatis redeploy bot setelah push ke `main` (±1–2 menit).

Cek versi bot live: buka `https://bukuwarung-ai-larisai.up.railway.app/` → field `bot_logic_version`.

---

## Struktur repo

```
bukuwarung-ai/
├── paths.py               # Root project — portable path helper
├── log_config.py          # Logging terpusat
├── app.py                 # Dashboard Streamlit
├── laris_core.py          # Logika bisnis bersama (Supabase + Groq)
├── kita-cuan-wa-bot/      # FastAPI webhook WhatsApp
│   ├── main.py            # ← SATU-SATUNYA file bot (jangan duplikat di root)
│   └── orchestrator.py    # Admin AI → Logistik AI
├── sql/                   # Script Supabase
├── docs/                  # Panduan
├── site/                  # Landing HTML
└── setup_laris_ai.sql     # Migrasi database utama
```
