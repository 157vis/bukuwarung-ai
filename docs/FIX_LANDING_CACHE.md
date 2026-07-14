# Panduan Fix: Landing Page `www.larisai.my.id` Masih Model Lama

## Status Saat Ini

| Item | Status |
|---|---|
| Repo `static/laris-landing.html` (lokal) | Model BARU (23 KB) |
| GitHub `main` branch (commit `45a7ec5`) | Model BARU (23 KB) |
| Cloudflare Pages deploy status | Succeeded 4 jam lalu |
| Cloudflare Pages serve `laris-landing.html` | Model LAMA (62 KB) |
| `www.larisai.my.id` serve | Model LAMA (62 KB) |

**Penyebab:** Cloudflare Pages deploy sukses secara metadata, tapi file `static/laris-landing.html` yang lama masih di-serve. Ini bug caching internal Pages.

---

## Solusi A: Purge Cache di Cloudflare Dashboard (Cepat)

### Step 1: Login Dashboard
1. Buka: https://dash.cloudflare.com
2. Pilih account Anda (yang punya domain `larisai.my.id`)
3. Klik domain **`larisai.my.id`**

### Step 2: Purge Cache
1. Menu kiri → klik **"Caching"** → sub-tab **"Configuration"**
2. Scroll ke bawah sampai ketemu tombol **"Purge Cache"**
3. Klik tombol **"Purge Everything"** (merah/oranye)
4. Konfirmasi: klik **"Purge Everything"** lagi
5. Tunggu 30 detik

### Step 3: Verifikasi
Buka browser **Incognito/Private** (Ctrl+Shift+N), akses:
- https://www.larisai.my.id/laris-landing.html

Jika masih model lama, lanjut ke **Solusi B**.

---

## Solusi B: Retry Deployment di Workers & Pages

### Step 1: Buka Pages Project
1. Buka: https://dash.cloudflare.com
2. Menu kiri → **"Workers & Pages"**
3. Klik project **`laris-landing`**

### Step 2: Cek Deployment History
1. Klik tab **"Deployments"** (di atas)
2. Lihat list deployment. Yang terbaru seharusnya commit `45a7ec5`
3. Klik deployment terbaru tersebut
4. Klik **"Retry deployment"** (kanan atas)
5. Tunggu 2-5 menit sampai status "Success"

### Step 3: Verifikasi
Buka browser **Incognito/Private**:
- https://www.larisai.my.id/laris-landing.html

---

## Solusi C: Hapus & Buat Ulang Project (Paling Pasti, Tapi Risiko)

⚠️ **Hanya jika A & B gagal.** Hapus project `laris-landing`, lalu buat ulang dengan setting:
- **Project name**: `laris-landing`
- **Source**: `157vis/bukuwarung-ai`
- **Branch**: `main`
- **Build command**: (kosong)
- **Build output**: `/` (default)
- **Root directory**: (kosong)

Setelah deploy sukses, re-link `www.larisai.my.id`:
1. Pages project → tab **"Custom domains"**
2. Klik **"Set up a custom domain"**
3. Masukkan: `www.larisai.my.id`
4. Cloudflare otomatis tambahkan CNAME di DNS
5. Tunggu propagasi 5-10 menit

---

## Solusi D: Cek Apakah Branch yang Di-Watch Benar

1. Pages project → tab **"Settings"** → **"Build"**
2. Pastikan:
   - **Production branch**: `main` (bukan `master` atau branch lain)
   - **Build command**: (kosong)
   - **Build output directory**: `/` atau kosong
   - **Root directory (advanced)**: (kosong)
3. Jika Production branch salah, ganti ke `main` lalu klik **"Save"**

---

## Solusi E: Force Redeploy via GitHub (Commit Kosong)

Jika dashboard bilang deploy sukses tapi file tidak ter-update, **commit kosong** bisa re-trigger webhook:

```bash
git commit --allow-empty -m "chore: trigger Cloudflare Pages redeploy"
git push origin main
```

Tunggu 2-5 menit lalu cek lagi.

---

## Urutan yang Saya Rekomendasikan

1. **Solusi A (Purge Cache)** — paling cepat, 90% kasus solved
2. **Solusi B (Retry Deployment)** — jika Purge Cache tidak cukup
3. **Solusi E (Commit Kosong)** — jika A & B gagal

---

## Verifikasi Final (Setelah Fix)

Buka https://www.larisai.my.id dan lihat:
- Hero section dengan **3D model interaktif** (bukan gambar statis)
- Animasi smooth saat scroll
- File size di DevTools → Network: file HTML sekitar 23 KB (bukan 65 KB)

Caranya cek ukuran di browser:
1. Tekan **F12** (buka DevTools)
2. Tab **"Network"**
3. Refresh halaman (F5)
4. Klik request `laris-landing.html`
5. Lihat **"Size"** di kolom kanan: harusnya **~23 KB**, bukan 65 KB
