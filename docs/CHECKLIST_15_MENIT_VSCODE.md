# Checklist 15 Menit (VS Code) - laris.AI

Panduan cepat ini khusus untuk setup lokal di laptop Anda.

## 0) Data yang dipakai di project ini

- Repo: `https://github.com/157vis/bukuwarung-ai`
- Supabase URL: `https://tagyexrsuvogrlhcthcp.supabase.co`
- BukuWarung CS (Railway): `https://bukuwarung-ai-larisai.up.railway.app`
- Bot AI Catat (Railway): `https://kita-cuan-wa-bot-larisai.up.railway.app`

---

## 1) Buka project di VS Code

```bash
git clone https://github.com/157vis/bukuwarung-ai.git
cd bukuwarung-ai
code .
```

---

## 2) Buat venv dan install (3 menit)

Di terminal VS Code:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 3) Isi secrets dashboard (2 menit)

Copy file:

- `.streamlit/secrets.toml.example` -> `.streamlit/secrets.toml`

Isi minimal:

```toml
SUPABASE_URL = "https://tagyexrsuvogrlhcthcp.supabase.co"
SUPABASE_KEY = "PASTE_ANON_KEY_ATAU_SERVICE_ROLE"
GROQ_API_KEY = "PASTE_GROQ_KEY"
BUKUWARUNG_BASE_URL = "https://bukuwarung-ai-larisai.up.railway.app"
CATAT_BOT_BASE_URL = "https://kita-cuan-wa-bot-larisai.up.railway.app"
```

> Untuk dashboard user biasa, anon key cukup.  
> Untuk setup/admin kadang lebih aman service_role.

---

## 4) Isi env bot AI Catat (2 menit)

Copy:

- `kita-cuan-wa-bot/.env.example` -> `kita-cuan-wa-bot/.env`

Isi minimal:

```env
SUPABASE_URL=https://tagyexrsuvogrlhcthcp.supabase.co
SUPABASE_KEY=PASTE_SERVICE_ROLE_KEY
GROQ_API_KEY=PASTE_GROQ_KEY
WA_PROVIDER=fonnte
WA_API_KEY=PASTE_TOKEN_FONNTE_BOT_CATAT
STOCK_THRESHOLD=5
REORDER_QTY=20
```

> Bot WA wajib `service_role` agar tidak mentok RLS.

---

## 5) Jalankan SQL Supabase (sekali) (2 menit)

Di Supabase SQL Editor jalankan:

1. `setup_laris_ai.sql`
2. `bukuwarung-ai/sql/fix_rls_bukuwarung.sql`
3. (opsional trial) `sql/seed_trial_products.sql`

---

## 6) Run dashboard lokal (1 menit)

Di root:

```powershell
streamlit run app.py
```

Buka:

- `http://localhost:8501`

Login super admin:

- `rafihrr1@gmail.com`

---

## 7) Run bot AI Catat lokal (1 menit)

Terminal baru:

```powershell
cd kita-cuan-wa-bot
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Cek:

- `http://localhost:8000/`

---

## 8) Setup 2 nomor WA dari dashboard (2 menit)

Di `Pengaturan`:

- Form **Tambah Client Baru (2 Nomor WA)** / **Update Dua Nomor WA Client**
  - `Nomor 1`: CS pelanggan
  - `Nomor 2`: AI Catat (owner kirim jual/beli)

Webhook Fonnte:

- CS -> `https://bukuwarung-ai-larisai.up.railway.app/webhook-whatsapp/{client_id}`
- AI Catat -> `https://kita-cuan-wa-bot-larisai.up.railway.app/webhook`

Setting Fonnte penting:

- `Autoread = ON`
- `Quick = OFF`
- `Autoreply template = OFF`

---

## 9) Test cepat (2 menit)

Kirim dari nomor owner (AI Catat):

- `jual kopi 50rb`

Harus muncul:

- transaksi di `Buku Kas` / `Ringkasan`
- log di `Ruang Komando` (Aktivitas WhatsApp)
- stok update di `Gudang`/`Produk` jika item terkait

---

## 10) Workflow harian git (30 detik)

```bash
git pull origin main
git add .
git commit -m "pesan perubahan"
git push origin main
```

