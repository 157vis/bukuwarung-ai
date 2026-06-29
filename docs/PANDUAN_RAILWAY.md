# Deploy laris.AI di Railway (Dashboard + Bot WA)

Supabase tetap di cloud (database). Railway men-host **2 service** dari repo GitHub yang sama.

```
[Laptop rumah] --git push--> [GitHub] --auto deploy--> [Railway]
                                                          |
                    +------------------+------------------+
                    |                                     |
            Service 1: Streamlit                   Service 2: FastAPI bot
            (dashboard publik)                     (webhook WhatsApp)
                    |                                     |
                    +------------------+------------------+
                                       v
                              [Supabase + Groq API]
```

---

## Yang perlu disiapkan

1. Akun **Railway** → [https://railway.app](https://railway.app) (login GitHub `157vis`)
2. Repo **157vis/bukuwarung-ai** sudah ter-push (branch `main`)
3. Key dari Supabase + Groq (sama seperti lokal)
4. Token **Fonnte/Wablas** (untuk bot WA)

---

## Langkah 1 — Buat project Railway

1. Railway → **New Project** → **Deploy from GitHub repo**
2. Pilih `**157vis/bukuwarung-ai`**
3. Railway akan buat 1 service pertama (kita ubah jadi dashboard)

---

## Langkah 2 — Service 1: Dashboard (Streamlit)

### Settings → Deploy


| Setting            | Nilai                               |
| ------------------ | ----------------------------------- |
| **Root Directory** | `/` (kosong / root repo)            |
| **Start Command**  | `bash scripts/railway-streamlit.sh` |


### Settings → Variables (Environment)


| Variable       | Nilai                                      |
| -------------- | ------------------------------------------ |
| `SUPABASE_URL` | `https://tagyexrsuvogrlhcthcp.supabase.co` |
| `SUPABASE_KEY` | **anon key** Supabase                      |
| `GROQ_API_KEY` | `gsk_...` (key valid)                      |


### Settings → Networking

- Klik **Generate Domain** → dapat URL seperti `https://bukuwarung-ai-production.up.railway.app`

Itu URL dashboard publik — buka dari laptop rumah, HP, mana saja.

---

## Langkah 3 — Service 2: Bot WhatsApp (FastAPI)

Di project Railway yang sama: **+ New Service** → **GitHub Repo** → pilih repo **sama**.

### Settings → Deploy


| Setting            | Nilai                         |
| ------------------ | ----------------------------- |
| **Root Directory** | `/` (root repo) |
| **Start Command**  | `bash scripts/railway-bot.sh` |

> **Satu file bot:** `kita-cuan-wa-bot/main.py` — script di atas otomatis `cd` ke folder itu lalu jalankan `uvicorn main:app`. Jangan pakai `main.py` di root repo (sudah dihapus).


### Settings → Variables


| Variable             | Nilai                                  |
| -------------------- | -------------------------------------- |
| `SUPABASE_URL`       | sama dengan dashboard                  |
| `SUPABASE_KEY`       | **service_role key** (WAJIB untuk bot) |
| `GROQ_API_KEY`       | `gsk_...`                              |
| `WA_PROVIDER`        | `fonnte` atau `wablas`                 |
| `WA_API_KEY`         | token provider WA                      |
| `STOCK_THRESHOLD`    | `5`                                    |
| `REORDER_QTY`        | `20`                                   |
| `WA_DEFAULT_USER_ID` | (opsional) user_id trial               |


### Settings → Networking

- **Generate Domain** → mis. `https://bukuwarung-ai-bot.up.railway.app`
- Webhook WA = `**https://<domain-bot>/webhook`**

Daftarkan URL webhook itu di dashboard **Fonnte/Wablas** (tidak perlu ngrok lagi).

---

## Langkah 4 — Tes dari rumah

1. Buka URL dashboard Railway → login admin
2. Buat client trial + hubungkan nomor WA
3. Jalankan `sql/seed_trial_products.sql` di Supabase (ganti `USER_ID_TRIAL`)
4. Kirim WA `jual indomie 5` ke nomor bot
5. Cek **Buku Kas** & **Ruang Komando** di dashboard

---

## Kerja dari laptop rumah (workflow)

```powershell
git clone https://github.com/157vis/bukuwarung-ai.git
cd bukuwarung-ai
# edit kode di Cursor/VS Code...
git add .
git commit -m "update fitur X"
git push
```

Railway **otomatis rebuild** kedua service setelah push ke `main`.

Tidak perlu menjalankan Streamlit/bot di laptop — cukup edit + push.  
Untuk tes lokal (opsional): salin `.streamlit/secrets.toml` + `kita-cuan-wa-bot/.env`.

---

## Halaman SEO (`site/`)

Folder `site/` (HTML statis) **tidak** dijalankan oleh script Railway di atas.

Pilihan:

- **GitHub Pages** (gratis, bagus untuk SEO) → deploy folder `site/`
- Atau service Railway ketiga dengan static file server (opsional)

Landing di dalam Streamlit (`static/laris-landing.html`) sudah ikut Service 1.

---

## Perbandingan singkat


| Platform                | Dashboard | Bot WA     | Gratis       | Cocok untuk                        |
| ----------------------- | --------- | ---------- | ------------ | ---------------------------------- |
| **Streamlit Cloud**     | ✅ mudah   | ❌ terpisah | ✅            | Cepat go-live dashboard saja       |
| **Railway (2 service)** | ✅         | ✅          | trial/kredit | **Semua online, kerja dari rumah** |
| Lokal + ngrok           | ✅         | ✅          | ✅            | Dev sementara                      |


---

## Troubleshooting


| Masalah                         | Solusi                                                                                                                                                                |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Build gagal                     | Cek **Deploy Logs** di Railway; pastikan `requirements.txt` root + `kita-cuan-wa-bot/requirements.txt` terinstall (Railway pakai root — gabung dependency jika perlu) |
| Dashboard blank / secrets error | Pastikan 3 env var Service 1 terisi                                                                                                                                   |
| Bot 502 / `Could not import module "main"` | Start Command = `bash scripts/railway-bot.sh` (bukan `uvicorn main:app` dari root). File bot: `kita-cuan-wa-bot/main.py`. |
| WA webhook tidak terpanggil     | URL harus `https://.../webhook` + HTTPS Railway domain                                                                                                                |
| AI tidak jalan                  | `GROQ_API_KEY` invalid di Variables Railway                                                                                                                           |


### Catatan dependency bot

Bot butuh paket dari `kita-cuan-wa-bot/requirements.txt` (fastapi, uvicorn, httpx, dotenv).  
Pastikan root `requirements.txt` sudah lengkap, atau Railway install keduanya — root `requirements.txt` saat ini:

```
streamlit
pandas
supabase
groq
fastapi
uvicorn
httpx
python-dotenv
```

(Tambahkan baris bot ke root `requirements.txt` jika build bot gagal import.)