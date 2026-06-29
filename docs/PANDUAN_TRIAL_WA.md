# Panduan Trial 1 Akun + Integrasi WhatsApp

Panduan praktis untuk **1 akun trial UMKM** + input lewat WhatsApp (AI Multi-Agent).

---

## Ringkasan alur

```
1. Admin buat akun trial + hubungkan nomor WA
2. Seed produk stok (opsional, untuk Logistik AI)
3. Jalankan bot WhatsApp (FastAPI) + webhook publik
4. Client kirim WA → bot → Supabase → dashboard (Ruang Komando)
```

---

## AI yang aktif di trial

| Agent | Peran |
|---|---|
| Admin AI | Catat transaksi, ringkasan, laporan KUR |
| Logistik AI | Pantau stok, usulkan restock |
| CS + Support AI | Respon chat pelanggan & komplain |
| Order + Payment AI | Alur order dan pembayaran pelanggan |

> Trial standar biasanya setara paket **Growth**: 2 nomor WA (CS + AI Catat).

---

## Langkah 1 — Database (sekali)

1. Jalankan **`setup_laris_ai.sql`** di Supabase SQL Editor (tabel + RLS).
2. Pastikan **GROQ_API_KEY** valid di:
   - `.streamlit/secrets.toml` (dashboard)
   - Streamlit Cloud Secrets (jika deploy)
   - `kita-cuan-wa-bot/.env` (bot)

---

## Langkah 2 — Buat 1 akun trial (Admin)

1. Buka dashboard → login **`Rafihrr1@gmail.com`**.
2. Menu **⚙️ Pengaturan** → **➕ Tambah Client Baru**:
   - **Email:** mis. `trial.warung@email.com`
   - **Password:** minimal 6 karakter (berikan ke calon trial)
   - **Nomor WhatsApp:** nomor HP yang akan dipakai kirim pesan ke bot (format `0812...`)
   - **Label:** mis. `Trial Warung Bu Sari`
3. **Catat `user_id`** yang muncul setelah client dibuat.

### Rekomendasi nomor (agar semua modul dashboard nyambung)

- **Nomor 1 (CS):** untuk chat pelanggan → webhook BukuWarung `/webhook-whatsapp/{client_id}`
- **Nomor 2 (AI Catat):** nomor owner untuk `jual/beli` → webhook bot catat `/webhook`

> Jika client tidak bisa login: matikan email confirmation di Supabase  
> (**Authentication → Providers → Email → Confirm email: OFF**)  
> atau buat user dengan **Auto Confirm** di Supabase Auth.

---

## Langkah 3 — Seed produk stok (agar Logistik AI jalan)

1. Buka **`sql/seed_trial_products.sql`**.
2. Ganti `'USER_ID_TRIAL'` dengan `user_id` dari langkah 2.
3. Jalankan di Supabase SQL Editor.

Contoh pesan WA setelah seed:
- `jual indomie 5` → stok indomie berkurang, jika di bawah ambang → approval di Ruang Komando.

---

## Langkah 4 — Setup bot WhatsApp

### 4a. File `.env` bot

Di folder `kita-cuan-wa-bot/`, isi `.env`:

```env
SUPABASE_URL=https://tagyexrsuvogrlhcthcp.supabase.co
SUPABASE_KEY=service-role-key-anda
GROQ_API_KEY=gsk_xxx
WA_PROVIDER=fonnte
WA_API_KEY=token-provider-wa-anda
STOCK_THRESHOLD=5
REORDER_QTY=20
```

> **WAJIB `service_role`** untuk bot (bypass RLS, tulis stok/approval).

### 4b. Jalankan bot

```powershell
cd kita-cuan-wa-bot
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Cek: buka `http://localhost:8000/` → status running.

### 4c. Expose webhook (tunnel)

```powershell
# pilih salah satu
ngrok http 8000
# atau
cloudflared tunnel --url http://localhost:8000
```

Salin URL HTTPS, mis. `https://xxxx.ngrok-free.app`.

### 4d. Daftarkan webhook di Fonnte (PENTING)

1. Login [fonnte.com](https://fonnte.com) → menu **Device** → **Edit** device Anda.
2. Isi **Webhook** (persis, tanpa spasi):
   ```
   https://kita-cuan-wa-bot-larisai.up.railway.app/webhook
   ```
3. **Autoread = ON** ← wajib, tanpa ini Fonnte tidak mengirim pesan masuk ke webhook.
4. **Personal = ON** (chat pribadi ke device).
5. **Quick = OFF** ← wajib OFF, cegah bot baca pesan kiriman sendiri (loop).
6. **Matikan template Autoreply** (menu Autoreply) — bentrok dengan webhook custom.
7. Device status **Connected** (hijau).
8. `WA_API_KEY` di Railway = **token device yang sama** di menu Device Fonnte.

> **Autoread ≠ Autoreply.** Autoread harus ON. **Quick harus OFF** (anti-loop). Autoreply template harus OFF.

Setelah simpan, kirim WA `test` → cek Railway Deploy Logs ada baris `DEBUG webhook raw`.

---

## Langkah 5 — Tes end-to-end (checklist)

Dari HP (nomor yang dihubungkan di langkah 2), kirim ke nomor bot:

| Pesan | Agent | Hasil yang diharapkan |
|---|---|---|
| `jual indomie 5` | Admin + Logistik | Balasan konfirmasi + catat transaksi; stok indomie -5 |
| `beli gula 15000` | Admin | Pengeluaran tercatat di Buku Kas |
| Foto struk | Admin (vision) | Grand total jadi 1 transaksi pengeluaran |
| Voice note | Admin (Whisper) | Teks → transaksi (jika audio jelas) |

Di **dashboard client trial** (login email trial):

- **Buku Kas** → transaksi muncul
- **Ruang Komando** → approval Logistik (jika stok kritis)
- **Ringkasan / Laporan KUR** → data terisi

---

## Perintah bot yang didukung (contoh)

- **Catat transaksi:** teks natural (`jual nasi goreng 25 ribu`, `beli minyak 35000`)
- **Penjualan + stok:** `jual indomie 5`, `jual kopi 2`
- **Baca struk:** kirim foto struk belanja
- **Voice:** kirim voice note berisi transaksi
- **Hapus terakhir:** (jika diimplementasi di bot — cek `main.py`)

---

## Troubleshooting cepat

| Masalah | Solusi |
|---|---|
| **Bot balas berulang-ulang (loop kopi)** | Fonnte: **Quick OFF**; deploy bot terbaru (filter echo) |
| **Railway tidak ada log DEBUG** | Fonnte: **Autoread ON**, webhook URL benar, device Connected |
| Bot tidak balas | Cek webhook URL, `WA_API_KEY` = token device yang sama |
| `Nomor belum terdaftar` | Hubungkan nomor di **Pengaturan admin** (`wa_users`) |
| Transaksi tidak masuk dashboard | Pastikan `user_id` di `wa_users` = auth user client |
| Ruang Komando kosong | Pastikan tabel `approvals` ada dan stok produk benar (agar trigger approval jalan) |
| Logistik tidak buat approval | Jalankan `seed_trial_products.sql`; set `STOCK_THRESHOLD` |
| RLS error di dashboard | Pastikan login client (JWT diteruskan ke Supabase) |
| AI kosong / gagal | Cek GROQ_API_KEY valid; restart Streamlit/bot |

---

## Setelah trial sukses

1. Deploy dashboard → **Streamlit Cloud** (Secrets = sama dengan lokal).
2. Deploy bot → Railway/Render/VPS (URL webhook permanen, bukan ngrok).
3. Ganti copy landing sudah selaras (#12) — fokus Admin AI + Logistik AI.
4. Rotate Groq key jika pernah terekspos di chat/log.
