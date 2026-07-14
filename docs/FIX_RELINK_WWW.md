# 🚨 Panduan Fix: Re-link `www.larisai.my.id` ke Pages Project Baru

## ❗ Status Sekarang

- ✅ Project Pages sudah di-rename: `laris-landing-v2`
- ❌ DNS record `www.larisai.my.id` HILANG (5 records, sebelumnya 6)
- ⚠️ Cloudflare warning: "Visitors cannot reach www.larisai.my.id"
- 🎯 **Goal**: Tambah record `www` baru + link custom domain ke `laris-landing-v2`

---

## Step-by-Step

### Step 1: Tambah DNS Record `www` Baru

1. Login: https://dash.cloudflare.com
2. Klik domain **`larisai.my.id`**
3. Klik **"DNS"** → **"Records"**
4. Klik tombol **"+ Add record"** (kanan atas, biru)

5. Isi form:
   - **Type**: `CNAME`
   - **Name**: `www`
   - **Target**: `laris-landing-v2.pages.dev`
   - **Proxy status**: ☁️ **Proxied** (oranye, biar dapet Cloudflare CDN + SSL)
   - **TTL**: Auto

6. Klik **"Save"**

### Step 2: Buka Project Pages `laris-landing-v2`

1. Menu kiri → **"Workers & Pages"**
2. Klik project **`laris-landing-v2`** (project yang baru di-rename)

### Step 3: Set Custom Domain

1. Klik tab **"Custom domains"**
2. Klik tombol **"Set up a custom domain"**
3. Masukkan: `www.larisai.my.id`
4. Klik **"Continue"**

Cloudflare akan otomatis:
- Verifikasi DNS record `www` (yang baru kita buat di Step 1)
- Setup SSL/TLS otomatis
- Aktifkan custom domain

5. Tunggu 1-3 menit sampai status **"Active"** (hijau)

### Step 4: Verifikasi

Buka browser **Incognito** (Ctrl+Shift+N):
- https://www.larisai.my.id/laris-landing.html

Cek DevTools (F12) → Network:
- **Status**: 200 OK
- **Size**: ~24 KB (uncompressed) atau ~7 KB (gzip)
- **Content-Encoding**: gzip atau br

Lihat **Title tab browser**:
- **Model BARU**: "Preview Landing laris.AI"
- **Model LAMA**: "laris.AI - Partner AI UMKM Indonesia | Catat Keuangan & Stok via WhatsApp"

### Step 5: Verifikasi Model Baru

Di DevTools → Elements, cari:
- `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/...">` ← Model BARU punya ini
- `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.47.0/...">` ← Model BARU punya ini

**Cara paling mudah**: Bandingkan **Title** di tab browser.

---

## ⏱️ Estimasi Waktu

- Step 1 (Tambah DNS): 1 menit
- Step 2-3 (Link custom domain): 2 menit
- Step 4-5 (Verifikasi): 2-3 menit

**Total: ~5-7 menit**

---

## 🆘 Troubleshooting

### "Custom domain already in use"

Jika muncul error "Custom domain already in use" di Step 3:

1. Cek apakah `www.larisai.my.id` masih linked ke project `laris-landing` (nama lama)
2. Buka project **`laris-landing`** (nama lama) → tab **"Custom domains"**
3. Cari `www.larisai.my.id` di list
4. Klik **"..."** di kanan → **"Remove"**
5. Tunggu 1-2 menit
6. Kembali ke project `laris-landing-v2` → Step 3 lagi

### "CNAME already exists"

Jika di Step 1 muncul error "CNAME already exists":

1. Cek list records, mungkin record `www` yang lama sebenarnya masih ada (hidden)
2. Refresh halaman (Ctrl+F5)
3. Cari record dengan Name `www` (case insensitive)
4. Jika ada, klik **"Edit"** → ganti Target ke `laris-landing-v2.pages.dev` → **"Save"**

### "SSL/TLS provisioning failed"

Jika SSL/TLS tidak auto-setup:

1. Pages project → tab **"Custom domains"** → klik `www.larisai.my.id`
2. Lihat **"SSL/TLS"** section
3. Pilih **"Full"** atau **"Full (Strict)"** encryption mode
4. Tunggu 5-10 menit untuk provisioning

---

## 💡 Catatan Penting

- **DNS Proxy (oranye ☁️)**: WAJIB untuk dapet SSL/TLS + CDN cache. Jangan pilih "DNS only" (abu-abu)
- **Build output directory**: Pastikan `/` (default), bukan `/static`
- **Custom domain propagation**: Biasanya 1-5 menit, kadang sampai 30 menit
