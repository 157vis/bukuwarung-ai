# Panduan Menambah Client Baru & Setup WhatsApp Bot (Laris.AI)

Panduan ini untuk **Admin Super** (`Rafihrr1@gmail.com`). Hanya admin yang boleh
menambah & mengedit client. Tujuan: dari nol sampai bot WhatsApp client siap
dipakai untuk test ke customer.

---

## 0. Prasyarat (sekali saja)

1. **Tabel database sudah dibuat di Supabase.**
  - Buka Supabase → **SQL Editor** → tempel isi `sql/setup_laris_ai.sql` → **Run**.
  - Script ini membuat tabel `approvals`, `wa_messages`, `wa_users`, lalu
  `NOTIFY pgrst, 'reload schema';` agar API langsung mengenali tabel baru.
2. **Secrets aplikasi Streamlit** (`.streamlit/secrets.toml`):
  ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "anon-key-anda"      # cukup anon key untuk dashboard
   GROQ_API_KEY = "gsk_xxx"
  ```
3. **Akun Admin Super sudah ada.**
  - Jika `Rafihrr1@gmail.com` belum terdaftar, buat sekali lewat Supabase →
   **Authentication → Users → Add user** (set email + password, centang
   *Auto Confirm*). Setelah itu login di dashboard pakai akun ini.

---

## 1. Login sebagai Admin Super

1. Jalankan dashboard: `streamlit run app.py`.
2. Klik **Masuk ke Dashboard** → login dengan `Rafihrr1@gmail.com`.
3. Tab **Daftar** sudah dihilangkan — pendaftaran client hanya lewat menu admin.

---

## 2. Buat Client Baru

1. Di sidebar pilih menu **⚙️ Pengaturan**.
  - Jika login sebagai admin, muncul tulisan *"Mode Admin Super aktif"*.
2. Bagian **➕ Tambah Client Baru**, isi:
  - **Email Client** — email usaha client.
  - **Password Sementara** — minimal 6 karakter (client bisa ganti nanti).
  - **Nomor WhatsApp (opsional)** — nomor WA bisnis client (`0812...` atau `62812...`).
  - **Nama Usaha / Label (opsional)** — mis. "Warung Bu Sari".
3. Klik **Buat Client**. Sistem menampilkan `user_id` client baru — **catat ID ini**.

> Catatan: jika di Supabase **Email Confirmation** aktif, akun client perlu
> verifikasi email sebelum bisa login. Untuk test cepat, matikan konfirmasi di
> Supabase (**Authentication → Providers → Email → Confirm email: off**) atau
> buat user via **Add user** dengan *Auto Confirm*.

---

## 3. Hubungkan / Tambah Nomor WhatsApp Client

Kalau nomor belum diisi saat membuat client, atau client punya beberapa nomor:

1. Di **⚙️ Pengaturan** → bagian **🔗 Hubungkan Nomor WA ke Client**.
2. Isi **User ID Client** (dari langkah 2), **Nomor WhatsApp**, **Label** (opsional).
3. Klik **Hubungkan**. Nomor otomatis dinormalisasi ke format `62...`.

Daftar semua client & nomornya tampil di **📋 Semua Client Terdaftar** (bisa **Hapus**).

---

## 4. Setup WhatsApp Bot untuk Client

Bot berada di folder `kita-cuan-wa-bot/` (FastAPI). Satu bot melayani semua
client karena pengirim diidentifikasi dari nomor WA → `user_id` (tabel `wa_users`).

1. **Konfigurasi `kita-cuan-wa-bot/.env`:**
  ```env
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_KEY=service-role-key      # WAJIB service_role agar bisa tulis stok/approval
   GROQ_API_KEY=gsk_xxx
   WA_PROVIDER_TOKEN=token-fonnte-atau-wablas
   STOCK_THRESHOLD=5
   REORDER_QTY=20
   WA_DEFAULT_USER_ID=               # opsional, fallback bila nomor belum terdaftar
  ```
  > Gunakan **service_role key** (bukan anon) untuk bot, karena RLS memblokir
  > tulis stok/approval dengan anon key.
2. **Jalankan bot:**
  ```bash
   cd kita-cuan-wa-bot
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8000
  ```
3. **Ekspos ke internet** (agar provider WA bisa kirim webhook):
  ```bash
   ngrok http 8000
  ```
   Salin URL https dari ngrok, mis. `https://xxxx.ngrok-free.app`.
4. **Daftarkan Webhook di provider WA (Fonnte/Wablas):**
  - Webhook URL: `https://xxxx.ngrok-free.app/webhook` (sesuaikan endpoint bot).
  - Sambungkan device/nomor WA bisnis client.

---

## 5. Test End-to-End

1. Dari HP, kirim pesan WA ke nomor bisnis client, contoh: `jual indomie 5`.
2. Bot membaca nomor → cari `user_id` di `wa_users` → proses AI → balas.
3. Bila stok menyentuh ambang (`STOCK_THRESHOLD`), Logistik AI membuat
  **approval** otomatis.
4. Buka dashboard → **Ruang Komando**: approval & riwayat chat muncul; admin/owner
  bisa **Setujui / Tolak**.

---

## 6. Checklist Cepat (sebelum demo ke customer)

- [ ] `sql/setup_laris_ai.sql` sudah dijalankan di Supabase yang benar.
- [ ] Admin Super bisa login.
- [ ] Client dibuat & `user_id` tercatat.
- [ ] Nomor WA client terhubung (cek di **📋 Semua Client Terdaftar**).
- [ ] Bot jalan (`uvicorn`) + ngrok aktif + webhook terdaftar.
- [ ] `SUPABASE_KEY` bot = **service_role**.
- [ ] Test kirim WA → balasan masuk → approval muncul di Ruang Komando.

---

## Troubleshooting Singkat


| Masalah                            | Penyebab umum                             | Solusi                                                                   |
| ---------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------ |
| `PGRST205 table not found`         | Tabel belum dibuat / cache PostgREST      | Jalankan `setup_laris_ai.sql` (ada `NOTIFY pgrst`) di project yang benar |
| Client tak bisa login              | Email belum dikonfirmasi                  | Matikan email confirmation atau pakai *Add user → Auto Confirm*          |
| Bot gagal tulis stok (`42501 RLS`) | Bot pakai anon key                        | Ganti `SUPABASE_KEY` bot ke **service_role**                             |
| Pesan WA tak dikenali user         | Nomor belum di `wa_users`                 | Hubungkan nomor di **Pengaturan** atau set `WA_DEFAULT_USER_ID`          |
| Webhook tak terpanggil             | URL ngrok salah / device WA belum connect | Cek URL webhook & status device di dashboard provider                    |


