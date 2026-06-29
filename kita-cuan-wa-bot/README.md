# Laris.AI — WhatsApp Bot

Bot WhatsApp yang reuse `laris_core.py` (Supabase + Groq). Satu sumber logika bisnis
dengan dashboard Streamlit, jadi data WA dan dashboard selalu sinkron.

**Entry point bot:** `main.py` di folder ini (satu-satunya — jangan buat salinan di root repo).

## Arsitektur singkat

```
Pelanggan/Owner  --WA-->  Fonnte/Wablas  --webhook-->  Bot (FastAPI)
                                                          |
                                          resolve_user_id_by_phone (tabel wa_users)
                                                          |
                                              laris_core (Supabase + Groq)
                                                          |
                                    transactions / approvals / wa_messages
                                                          |
                                          Dashboard Streamlit (Ruang Komando)
```

## 1. Prasyarat database (sekali saja)

Jalankan `../sql/setup_laris_ai.sql` di **Supabase → SQL Editor** (membuat tabel
`approvals`, `wa_messages`, `wa_users`, lalu `NOTIFY pgrst, 'reload schema'`).

> Jika dashboard masih bilang "tabel belum ada" padahal SQL sudah dijalankan:
> 1. Pastikan project Supabase di SQL Editor SAMA dengan `SUPABASE_URL` di `.env`/secrets.
> 2. Jalankan lagi: `NOTIFY pgrst, 'reload schema';`
> 3. Atau Dashboard Supabase → Settings → API → "Reload schema cache".

## 2. Setup bot

```bash
cd kita-cuan-wa-bot
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

Isi `.env`:
- `SUPABASE_URL` — sama dengan dashboard
- `SUPABASE_KEY` — **gunakan SERVICE_ROLE key** (Settings → API → service_role).
  Bot adalah backend; service_role bypass RLS sehingga bisa update stok `products`
  dan menulis ke `approvals`. (Dashboard Streamlit tetap pakai anon key.)
- `GROQ_API_KEY` — API key Groq
- `WA_PROVIDER` — `fonnte` atau `wablas`
- `WA_API_KEY` — token dari provider WA
- (opsional) `STOCK_THRESHOLD`, `REORDER_QTY`, `WA_DEFAULT_USER_ID`

Jalankan:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Cek sehat: buka `http://localhost:8000/` → harus muncul status running.

## 3. Hubungkan ke WhatsApp (webhook)

Bot perlu URL publik. Untuk lokal, pakai tunnel:

```bash
# pilih salah satu
ngrok http 8000
# atau
cloudflared tunnel --url http://localhost:8000
```

Lalu di dashboard provider:
- **Fonnte**: Device → Webhook URL = `https://<url-publik>/webhook`
- **Wablas**: Pengaturan → Webhook = `https://<url-publik>/webhook`

## 4. Cara menambah CLIENT BARU (admin only)

Pendaftaran client **hanya oleh Super Admin** (`Rafihrr1@gmail.com`) — tab Daftar sudah dihilangkan.

1. **Admin login** → menu **⚙️ Pengaturan → ➕ Tambah Client Baru** (email, password, nomor WA, label).
2. **Catat `user_id`** client → jalankan `../sql/seed_trial_products.sql` (ganti `USER_ID_TRIAL`) agar Logistik AI punya katalog stok.
3. **Selesai.** Saat client kirim WA ke nomor bot, `resolve_user_id_by_phone` mengenali nomor di `wa_users`.

> Panduan lengkap trial + WA: **`../docs/PANDUAN_TRIAL_WA.md`**

> Mode cepat (1 client / demo): set `WA_DEFAULT_USER_ID` di `.env` ke user_id trial.
> Semua pesan tanpa mapping akan masuk ke user itu.

## 5. Tes alur lengkap

Kirim ke nomor bot via WhatsApp (atau simulasikan POST ke `/webhook`):

```
jual indomie 5
```

Hasil yang diharapkan:
- Bot balas "✅ Tercatat!" + (jika stok produk < ambang) catatan dari **Logistik AI**.
- Approval PO muncul di **Ruang Komando** dashboard → tombol **Setujui / Tolak**.
- Percakapan muncul di widget **Aktivitas WhatsApp**.

Format payload Fonnte (resmi): `sender`, `message`, `url`, `extension`, `inboxid`  
Simulasi curl: `{ "sender": "62812xxxx", "message": "jual indomie 5" }`

> **Penting Fonnte:** matikan **autoreply bawaan** di dashboard Fonnte jika pakai webhook custom — autoreply Fonnte dan webhook saling bentrok.
