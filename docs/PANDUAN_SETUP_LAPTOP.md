# Panduan Setup di Laptop (sync GitHub)

Semua kode sudah di **GitHub** — tidak tersimpan hanya di satu komputer. Laptop dan PC rumah memakai repo yang sama.

**Repo:** https://github.com/157vis/bukuwarung-ai  
**Branch kerja:** `main`

---

## 1. Clone pertama kali

### Windows (PowerShell / Git Bash)

```powershell
cd C:\Users\NAMA_ANDA\Projects
git clone https://github.com/157vis/bukuwarung-ai.git
cd bukuwarung-ai
```

### macOS / Linux

```bash
cd ~/Projects
git clone https://github.com/157vis/bukuwarung-ai.git
cd bukuwarung-ai
```

Login GitHub jika diminta (browser atau Personal Access Token).

---

## 2. Python & dependensi

```bash
python -m venv .venv
```

Aktifkan venv:

- **Windows:** `.venv\Scripts\activate`
- **macOS/Linux:** `source .venv/bin/activate`

```bash
pip install -r requirements.txt
pip install -r kita-cuan-wa-bot/requirements.txt
```

---

## 3. File rahasia (tidak ada di GitHub)

Git sengaja **mengabaikan** file berisi API key. Buat manual di laptop:

### Dashboard Streamlit

```bash
copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # Windows
# cp .streamlit/secrets.toml.example .streamlit/secrets.toml    # Mac/Linux
```

Isi `secrets.toml`:

```toml
SUPABASE_URL = "https://tagyexrsuvogrlhcthcp.supabase.co"
SUPABASE_KEY = "anon-key-dari-supabase"
GROQ_API_KEY = "gsk_..."
```

### Bot WhatsApp (jika jalankan lokal)

```bash
copy kita-cuan-wa-bot\.env.example kita-cuan-wa-bot\.env
```

Isi `.env` — lihat `kita-cuan-wa-bot/.env.example`. Untuk production Railway, pakai **service_role** Supabase.

> **Tips:** Salin isi `secrets.toml` / `.env` dari komputer lama lewat password manager atau chat terenkripsi — jangan commit ke git.

---

## 4. Jalankan aplikasi

### Dashboard

```bash
streamlit run app.py
```

Buka http://localhost:8501 — login pakai email **client** (bukan admin), mis. `rafiharliansyah34@gmail.com`.

### Bot WA (opsional lokal)

```bash
cd kita-cuan-wa-bot
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> File bot hanya **`kita-cuan-wa-bot/main.py`** — tidak ada salinan di folder root.

Bot production sudah jalan di Railway — laptop biasanya hanya edit kode + push, tidak perlu jalankan bot lokal.

---

## 5. Sync antar perangkat

### Di komputer A — selesai kerja

```bash
git status
git add .
git commit -m "Jelaskan perubahan singkat"
git push origin main
```

### Di laptop B — mulai kerja

```bash
git pull origin main
```

Selalu **pull dulu** sebelum edit agar tidak bentrok.

---

## 6. Cek bot sudah ter-update (Railway)

Setelah `git push`, tunggu 1–2 menit lalu buka:

https://bukuwarung-ai-larisai.up.railway.app/

Contoh respons:

```json
{
  "status": "laris.AI WA Bot is running",
  "bot_logic_version": "2026-06-27-logistik-orchestrator-v4"
}
```

Jika versi belum berubah, cek tab **Deployments** di Railway dashboard.

---

## 7. Git belum dikenali di terminal?

Di Windows, Git biasanya terpasang di:

`C:\Program Files\Git\cmd\git.exe`

Tambahkan ke PATH: **Settings → System → About → Advanced → Environment Variables** → Path → tambah `C:\Program Files\Git\cmd`.

Atau pakai **Git Bash** / **GitHub Desktop**.

---

## 8. Checklist pertama kali di laptop

- [ ] `git clone` berhasil
- [ ] `pip install` tanpa error
- [ ] `secrets.toml` dan `.env` sudah diisi
- [ ] `streamlit run app.py` → dashboard terbuka
- [ ] `git pull` / `git push` berhasil
- [ ] Tes WA: `jual kopi 35000` (setelah SQL kopi di Supabase)

SQL stok kopi trial: jalankan `sql/update_kopi_stock.sql` di Supabase.

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `git: command not found` | Install Git for Windows / tambah ke PATH |
| Push ditolak | `git pull origin main` dulu, selesaikan konflik, push lagi |
| Dashboard kosong | Login email **client**, bukan admin |
| Bot tidak balas | Cek Fonnte webhook + Autoread ON (lihat `PANDUAN_TRIAL_WA.md`) |
| KeyError SUPABASE | File `.env` / `secrets.toml` belum dibuat |
