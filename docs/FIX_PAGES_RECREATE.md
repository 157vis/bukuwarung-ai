# 🚨 Panduan Fix: Hapus & Buat Ulang Project Cloudflare Pages

## ❗ Masalah

Cloudflare Pages dashboard bilang deployment commit `45a7ec5` sukses 1 jam lalu, **TAPI file HTML yang di-serve masih model lama (62KB)**. Bahkan di deployment URL unik `eba68b5b.laris-landing.pages.dev/laris-landing.html` (spesifik untuk commit itu) masih model lama.

**Diagnosis**: Build cache Cloudflare Pages untuk project `laris-landing` STUCK. Pages tidak benar-benar re-render file static dari GitHub.

## ✅ Solusi: Hapus & Buat Ulang Project Pages

### Step 1: Catat Konfigurasi Saat Ini

Sebelum hapus, catat dulu:
- **Project name**: `laris-landing`
- **Source**: `157vis/bukuwarung-ai` (GitHub)
- **Branch**: `main`
- **Build command**: (kosong)
- **Build output directory**: `/` (default)
- **Root directory**: (kosong)
- **Custom domain**: `www.larisai.my.id`

### Step 2: Hapus Project

1. Buka: https://dash.cloudflare.com
2. Menu kiri → **"Workers & Pages"**
3. Klik project **`laris-landing`**
4. Klik tab **"Settings"** (paling kanan)
5. Scroll ke bawah sampai ketemu **"Delete Project"** (merah)
6. Klik **"Delete Project"**
7. Konfirmasi dengan mengetik nama project: `laris-landing`
8. Klik **"Delete"**

### Step 3: Hapus DNS Record (Opsional, Tapi Disarankan)

1. Menu kiri → klik domain **`larisai.my.id`**
2. Klik **"DNS"** → **"Records"**
3. Cari record `www` (Type: CNAME, Name: `www`, Content: `laris-landing.pages.dev`)
4. Klik **"Edit"** di kanan → klik **"Delete"**
5. Konfirmasi

> **Alasan**: DNS record ini akan di-recreate otomatis oleh Pages setelah project baru dibuat.

### Step 4: Buat Project Baru

1. Menu kiri → **"Workers & Pages"**
2. Klik tombol **"Create application"** (kanan atas)
3. Pilih tab **"Pages"**
4. Klik **"Connect to Git"**
5. Pilih **"GitHub"**
6. Pilih repository: **`157vis/bukuwarung-ai`**
7. Klik **"Begin setup"**

### Step 5: Konfigurasi Project Baru

- **Project name**: `laris-landing` (sama, atau bebas - tapi nanti URL Pages akan beda)
  - **Catatan**: Jika nama project sama (`laris-landing`), URL `laris-landing.pages.dev` tetap sama
- **Production branch**: `main`
- **Build command**: (kosong)
- **Build output directory**: `/` (default)
- **Root directory (advanced)**: (kosong, default `/`)
- **Environment variables**: (tidak perlu, tidak ada yang dipakai)

### Step 6: Deploy

1. Klik **"Save and Deploy"**
2. Tunggu 1-3 menit sampai deployment sukses
3. Cloudflare otomatis sediakan URL: `https://laris-landing.pages.dev`

### Step 7: Verifikasi File Baru

Buka di browser Incognito:
- https://laris-landing.pages.dev/laris-landing.html

Cek ukuran file:
1. Tekan **F12** → tab **"Network"**
2. Refresh halaman
3. Klik request `laris-landing.html`
4. Lihat **"Size"**: harusnya **~23 KB** (bukan 65 KB)

### Step 8: Re-link Custom Domain

1. Di project baru, klik tab **"Custom domains"**
2. Klik **"Set up a custom domain"**
3. Masukkan: `www.larisai.my.id`
4. Klik **"Continue"**
5. Cloudflare otomatis:
   - Tambahkan CNAME record di DNS
   - Setup SSL/TLS otomatis
6. Tunggu 5-10 menit untuk propagasi

### Step 9: Verifikasi Final

Buka browser Incognito:
- https://www.larisai.my.id/laris-landing.html

---

## ⏱️ Estimasi Waktu

- Step 1-3 (Hapus): 5 menit
- Step 4-6 (Buat ulang): 5 menit
- Step 7 (Build & deploy): 3 menit
- Step 8 (Link domain): 2 menit
- Step 9 (Propagasi DNS): 5-10 menit

**Total: ~20-25 menit**

---

## 🆘 Jika Masih Gagal

Jika setelah hapus & buat ulang file masih model lama, kemungkinan:
1. **DNS cache komputer** — buka browser dengan `chrome://net-internals/#dns` lalu "Clear host cache"
2. **File GitHub belum benar-benar berubah** — verifikasi di https://github.com/157vis/bukuwarung-ai/blob/main/static/laris-landing.html
3. **Ada CDN lain di depan** — cek apakah ada reverse proxy lain
