# 🎯 Panduan Fix: Drag & Drop Landing Page ke Cloudflare Pages

## ❗ Kenapa Drag & Drop?

Project `laris-landing` lama **stuck** — rename tidak bekerja, build cache tidak invalidate. Solusi: hapus project lama, upload file langsung via drag & drop.

**Keuntungan drag & drop**:
- ✅ Tidak ada build cache
- ✅ Tidak ada Git integration complications
- ✅ File yang di-upload = file yang di-serve (pasti update)
- ✅ Selesai dalam 2-3 menit

---

## 📁 File yang Sudah Disiapkan

Folder: **`C:\Users\Teknik SAP MTAL\bukuwarungai\pages-deploy\`**

Isi:
- `index.html` (23.510 bytes — model baru 3D interaktif)

File ini **self-contained** — semua CSS & JavaScript sudah di-inline. Hanya load Bootstrap & Tabler Icons dari CDN eksternal.

---

## Step-by-Step

### Step 1: Hapus Project `laris-landing` (yang stuck)

1. Login: https://dash.cloudflare.com
2. Menu kiri → **"Workers & Pages"**
3. Klik project **`laris-landing`** (atau nama apapun yang ada)
4. Tab **"Settings"** (paling kanan)
5. Scroll ke bawah → **"Delete Project"** (tombol merah)
6. Konfirmasi dengan ketik nama project → **"Delete"**
7. Tunggu 1-2 menit sampai project hilang

### Step 2: Buka Halaman Create Pages Baru

1. **Workers & Pages** → **"Create application"**
2. Pilih tab **"Pages"**
3. Klik **"Get started"** di opsi **"Drag and drop your files"**

### Step 3: Drag & Drop File

1. Buka **File Explorer** Windows
2. Navigasi ke: `C:\Users\Teknik SAP MTAL\bukuwarungai\pages-deploy\`
3. **Drag folder `pages-deploy`** ke area upload di Cloudflare Dashboard
4. **Project name**: `laris-landing-2026` (atau nama unik lain)
5. Tunggu upload selesai (1-2 menit untuk 23 KB)

### Step 4: Deploy

Cloudflare akan otomatis deploy. Tunggu 1-2 menit.

URL baru: `https://laris-landing-2026.pages.dev/`

### Step 5: Verifikasi

Buka browser **Incognito** (Ctrl+Shift+N):
- https://laris-landing-2026.pages.dev/

Cek:
- **Title tab browser**: "Preview Landing laris.AI"
- **DevTools (F12) → Network** → `index.html` size: **~24 KB**
- **Hero section** dengan 3D model interaktif

### Step 6: Tambah DNS Record `www`

1. Menu kiri → klik domain **`larisai.my.id`**
2. **DNS** → **"Records"**
3. Klik **"+ Add record"**
4. Isi:
   - **Type**: `CNAME`
   - **Name**: `www`
   - **Target**: `laris-landing-2026.pages.dev`
   - **Proxy**: ☁️ **Proxied** (oranye)
   - **TTL**: Auto
5. **Save**

### Step 7: Link Custom Domain

1. Kembali ke **Workers & Pages** → project **`laris-landing-2026`**
2. Tab **"Custom domains"**
3. Klik **"Set up a custom domain"**
4. Masukkan: `www.larisai.my.id`
5. **Continue**
6. Tunggu status **"Active"** (1-3 menit)

### Step 8: Verifikasi Final

Buka **browser Incognito**: https://www.larisai.my.id/

Landing page baru (3D interaktif) harusnya live.

---

## ⏱️ Estimasi Waktu

- Step 1 (Hapus project): 2 menit
- Step 2-4 (Drag & drop + deploy): 3 menit
- Step 5 (Verifikasi Pages URL): 1 menit
- Step 6 (Tambah DNS): 1 menit
- Step 7 (Link custom domain): 2 menit
- Step 8 (Verifikasi final): 2-3 menit propagasi

**Total: ~12-15 menit**

---

## 🆘 Troubleshooting

### "Project name already taken"

Jika `laris-landing-2026` sudah ada, gunakan nama lain:
- `laris-landing-jul26`
- `larisai-landing`
- `laris-landing-prod`

### Drag & Drop Tidak Berfungsi

1. Pastikan browser support (Chrome, Edge, Firefox modern)
2. Coba dengan **file individual** (bukan folder):
   - Drag file `index.html` saja
3. Atau gunakan **"Create a deployment via Wrangler"** (alternatif CLI)

### Custom Domain Error "Already in use"

Jika muncul error di Step 7:

1. Buka project `laris-landing` (nama lama, mungkin masih ada)
2. Tab **Custom domains** → cari `www.larisai.my.id` → klik **"..."** → **"Remove"**
3. Atau langsung buat record DNS baru yang point ke project baru

### File Upload Gagal / Timeout

1. Cek koneksi internet
2. Refresh halaman (Ctrl+F5)
3. Coba dengan file lebih kecil (compress HTML dulu)

---

## 💡 Tips Penting

- **Jangan rename project lagi** — buat baru dengan nama unik
- **Selalu gunakan browser Incognito** untuk verifikasi
- **Cek DevTools Network** untuk ukuran file asli (vs DevTools "Size" yang sudah compressed)
- **DNS Proxy (oranye) WAJIB** untuk SSL/TLS + Cloudflare CDN
