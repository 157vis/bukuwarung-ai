# 🚨 Panduan Fix: Rename Project Pages (Tanpa Hapus DNS)

## ❗ Masalah Sebelumnya

User coba hapus DNS record `www.larisai.my.id` untuk re-link, tapi dapat error:
```
An unknown error occurred. Please try again.
Record ID 69e168a11b9c80d1889321b126796f19 does not exist.
```

**Penyebab**: Cloudflare lock record `www` karena linked ke Pages project. Tidak bisa di-hapus dari DNS, harus dari Pages dashboard.

## ✅ Solusi Baru: Rename Project Pages (Paling Aman)

Kita rename project `laris-landing` → `laris-landing-v2` di Cloudflare Dashboard:
- Trigger fresh build dengan artifact baru
- Cloudflare otomatis update custom domain link
- DNS record `www` akan otomatis update ke `laris-landing-v2.pages.dev`

---

## Step-by-Step

### Step 1: Buka Project Pages

1. Login: https://dash.cloudflare.com
2. Menu kiri → **"Workers & Pages"**
3. Klik project **`laris-landing`**

### Step 2: Rename Project

1. Klik tab **"Settings"** (paling kanan)
2. Scroll ke bagian **"Project name"** (paling atas)
3. Klik **"Project name"** atau tombol rename
4. Ganti dari `laris-landing` menjadi **`laris-landing-v2`**
5. Klik **"Save"**
6. Konfirmasi rename

**Tunggu 1-2 menit** sampai perubahan propagasi.

### Step 3: Trigger Redeploy

Karena rename, Cloudflare biasanya otomatis trigger deployment baru. Tapi kalau tidak:

1. Klik tab **"Deployments"**
2. Klik **"Retry deployment"** di deployment terbaru
3. Tunggu 2-3 menit sampai build selesai

### Step 4: Verifikasi Model Baru

Buka browser **Incognito** (Ctrl+Shift+N):
- https://laris-landing-v2.pages.dev/laris-landing.html

Cek ukuran:
1. Tekan **F12** → tab **"Network"**
2. Refresh halaman (F5)
3. Klik request `laris-landing.html`
4. Lihat **"Size"**: harusnya **~24 KB** (gzip ~7 KB)
5. **PENTING**: Lihat juga **"Content-Encoding"** di Response Headers — harusnya `gzip` atau `br`

Bandingkan dengan model lama:
| Indikator | Model LAMA | Model BARU |
|---|---|---|
| File size (uncompressed) | 62-65 KB | **24 KB** |
| gzip compressed | ~13 KB | ~7 KB |
| Has Bootstrap 5.3 CSS | ❌ | ✅ |
| Has tabler-icons 2.47.0 | ✅ | ✅ |
| Has three.module.js | ❌ | ❌ |
| Has koin_3d | ✅ | ✅ |
| Title | "Partner AI UMKM" | "Preview Landing laris.AI" |

**Cara paling mudah verifikasi model baru**: Lihat **Title** di tab browser.
- Model lama: `laris.AI - Partner AI UMKM Indonesia | Catat Keuangan & Stok via WhatsApp`
- Model baru: `Preview Landing laris.AI` (atau title yang lebih clean dari model baru)

### Step 5: Re-link Custom Domain

Setelah konfirmasi `laris-landing-v2.pages.dev` sudah serve model baru:

1. Di project Pages (sekarang namanya `laris-landing-v2`), klik tab **"Custom domains"**
2. Lihat apakah `www.larisai.my.id` masih linked atau hilang
3. **Jika hilang**: klik **"Set up a custom domain"** → masukkan `www.larisai.my.id` → klik **"Continue"**
4. **Jika masih ada**: klik **"..."** di kanan → **"Remove"** → lalu add ulang

### Step 6: Verifikasi DNS

1. Menu kiri → klik domain **`larisai.my.id`**
2. Klik **"DNS"** → **"Records"**
3. Cari record `www` (Type: CNAME, Content: `laris-landing-v2.pages.dev`)
4. **Pastikan ada** record ini. Cloudflare biasanya otomatis manage.
5. Jika `www` masih menunjuk `laris-landing.pages.dev` (nama lama), update manual:
   - Klik **"Edit"** di record `www`
   - Ganti Content dari `laris-landing.pages.dev` menjadi `laris-landing-v2.pages.dev`
   - Klik **"Save"**

### Step 7: Verifikasi Final

Buka browser **Incognito**:
- https://www.larisai.my.id/laris-landing.html

Tunggu 5-10 menit untuk propagasi DNS.

---

## 🆘 Jika Masih Model Lama

### Opsi A: Hapus & Buat Ulang Project (Cara Lama)

Ikuti `docs/FIX_PAGES_RECREATE.md` tapi **JANGAN hapus DNS record `www`**. Biarkan Cloudflare auto-manage. Setelah project baru dibuat, re-link dari tab Custom domains.

### Opsi B: Tunggu Invalidation Cache

Cloudflare cache kadang butuh waktu 1-24 jam untuk invalidate. Tunggu dan refresh berkala.

### Opsi C: Cek Build Output

1. Pages project → tab **"Settings"** → **"Build"**
2. Pastikan:
   - **Build command**: (kosong)
   - **Build output directory**: `/` (default — INI PENTING, jangan `/static` atau lainnya)
   - **Root directory**: (kosong)

Build output directory yang salah (misal `/static`) bisa menyebabkan file di-serve dari subfolder yang salah.

---

## ⏱️ Estimasi Waktu

- Step 1-3 (Rename + redeploy): 3 menit
- Step 4 (Verifikasi): 2 menit
- Step 5-6 (Re-link domain): 3 menit
- Step 7 (Propagasi): 5-10 menit

**Total: ~15-20 menit**

---

## 💡 Tips

- **Selalu gunakan browser Incognito** untuk verifikasi agar tidak kena cache browser
- **Selalu cek DevTools Network tab** untuk ukuran file asli
- **Jangan hapus DNS record manual** untuk domain yang sudah linked ke Pages — biarkan Cloudflare auto-manage
