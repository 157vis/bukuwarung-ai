# 🔐 Fix Login Admin `rafihrr1@gmail.com`

## ✅ Code Status (SUDAH BENAR)

Di `app.py` line 35:
```python
SUPER_ADMIN_EMAILS = ("rafihrr1@gmail.com",)
```

`rafihrr1@gmail.com` **sudah satu-satunya super admin** (tuple 1 element, case-insensitive).

## ❓ Kemungkinan Penyebab Login Gagal

Meskipun user `rafihrr1@gmail.com` sudah ada di Supabase, login Streamlit masih bisa gagal karena:

1. **Password tidak cocok** — password yang Anda coba bukan yang tersimpan di Supabase
2. **Email belum terverifikasi** — Supabase butuh email konfirmasi (terkecuali `email_confirm=True` saat create)
3. **RLS Supabase di level API** memblokir `sign_in_with_password`

## ✅ Solusi: Reset Password Admin (2 Cara)

### 🏆 Cara 1: Pakai Supabase Dashboard (Paling Aman & Cepat)

1. Buka https://supabase.com/dashboard/project/tagyexrsuvogrlhcthcp/auth/users
2. Cari baris dengan email `rafihrr1@gmail.com`
3. Klik ikon **titik tiga (⋮)** di kanan baris user tersebut
4. Pilih **"Send password recovery"** → Supabase akan kirim link reset ke email
   - **ATAU** — kalau ini tidak praktis karena Anda tidak bisa akses email itu, gunakan Cara 2.

### 🏆 Cara 2: Hapus & Buat Ulang User (5 menit)

**Langkah A — Hapus user lama:**

1. Buka https://supabase.com/dashboard/project/tagyexrsuvogrlhcthcp/auth/users
2. Cari `rafihrr1@gmail.com` → klik ⋮ → **"Delete user"**
3. Konfirmasi delete

**Langkah B — Buat user baru:**

1. Masih di halaman yang sama, klik tombol hijau **"Add user"** (kanan atas) → **"Create new user"**
2. Isi form:
   ```
   Email              : rafihrr1@gmail.com
   Password           : LarisAdmin2024!   ← (pilih password kuat Anda sendiri)
   Auto Confirm User  : ✅ (CENTANG!)
   ```
3. Klik **"Create user"**
4. User baru muncul di tabel dengan `authenticated` role.

**Langkah C — Test login:**

1. Buka https://laris-ai.streamlit.app/?login=1
2. Masukkan:
   ```
   Email    : rafihrr1@gmail.com
   Password : LarisAdmin2024!   ← (yang Anda set di Langkah B)
   ```
3. Klik **Masuk** → harusnya langsung masuk dashboard

## 🔍 Cara Verifikasi: User Ini Benar-benar Ada

1. Buka https://supabase.com/dashboard/project/tagyexrsuvogrlhcthcp/auth/users
2. Lihat tabel:
   - Cari `rafihrr1@gmail.com`
   - Cek kolom **"Confirmed"** atau **"Email Confirmed At"**
   - Kalau **NULL/kosong** → user belum konfirmasi email → harus **CENTANG "Auto Confirm User"** saat create
   - Kalau **terisi tanggal** → user sudah confirmed, harusnya bisa login

## 🚨 Kalau Login Masih Gagal Setelah Buat Ulang

Cek error message di Streamlit:
- **"Email atau password salah"** → password salah, ulangi Cara 2 dengan password baru
- **"Gagal masuk: ..."** → copy paste error lengkapnya ke saya, biasanya masalah konfigurasi Supabase

## 🎁 Alternatif: Password Recovery via SQL (Tidak Disarankan)

Cara ini butuh akses SQL & generate bcrypt hash manual — terlalu ribet. Pakai Cara 1 atau 2 saja.
