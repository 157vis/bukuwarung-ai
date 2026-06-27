# Panduan Publish Website + SEO Google (Laris.AI)

Tujuan: website online & **muncul di halaman 1 Google** untuk kata kunci target
(mis. "AI kasir WhatsApp UMKM", "pencatatan keuangan WhatsApp", "Laris.AI").

> Penting dipahami dulu: aplikasi **Streamlit itu dinamis (SPA)** dan kurang
> ramah SEO — Google sulit meng-index isinya. Karena itu strateginya **dipisah**:
>
> 1. **Landing page statis** (HTML cepat, di-index Google) → untuk pemasaran/SEO.
> 2. **Aplikasi Streamlit** (dashboard) → di balik tombol **"Masuk"**.

---

## BAGIAN A — Publish Aplikasi (Dashboard Streamlit)

### Opsi 1: Streamlit Community Cloud (gratis, paling cepat)

1. Push project ke **GitHub** (repo privat boleh).
2. Buka [https://share.streamlit.io](https://share.streamlit.io) → **New app** → pilih repo, branch, file `app.py`.
3. Menu **Advanced settings → Secrets**, isi sama seperti `.streamlit/secrets.toml`:
  ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "anon-key"
   GROQ_API_KEY = "gsk_xxx"
  ```
4. Deploy → dapat URL `https://namaapp.streamlit.app`.

### Opsi 2: VPS / Railway / Render (kontrol penuh + domain sendiri)

- Jalankan: `python -m streamlit run app.py --server.port 8501 --server.headless true`
- Pasang reverse proxy (Nginx) + HTTPS (Let's Encrypt) → arahkan ke `app.larisai.id`.

### WhatsApp Bot (FastAPI)

- Deploy `kita-cuan-wa-bot/` terpisah (Railway/Render/VPS) dengan `SUPABASE_KEY` =
**service_role**. Daftarkan webhook publiknya di Fonnte/Wablas.

---

## BAGIAN B — Landing Page yang Bisa Juara di Google

Streamlit kurang baik untuk SEO, jadi buat **landing page statis** terpisah.

### 1. Hosting landing (gratis & cepat di-index)

- **Vercel / Netlify / GitHub Pages / Cloudflare Pages** — semua gratis & HTTPS.
- Struktur minimal:
  ```
  index.html      (halaman utama, isi konten SEO)
  robots.txt
  sitemap.xml
  ```
- Tombol **"Masuk ke Dashboard"** di landing → link ke URL Streamlit
(`https://app.streamlit.app` atau `app.larisai.id`).

### 2. Domain profesional

- Beli domain `.id` / `.com` (Niagahoster, Domainesia, Cloudflare).
- Landing → `https://larisai.id` ; aplikasi → `https://app.larisai.id`.
- Domain sendiri jauh lebih dipercaya Google daripada subdomain gratis.

---

## BAGIAN C — Checklist SEO Agar Naik ke Halaman 1

### 1. On-page (wajib di `index.html`)

```html
<head>
  <title>Laris.AI — AI Kasir & Keuangan via WhatsApp untuk UMKM</title>
  <meta name="description" content="Catat penjualan, stok, dan keuangan UMKM langsung dari WhatsApp dengan AI. Laporan KUR otomatis. Coba gratis.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://larisai.id/">

  <!-- Open Graph (tampilan saat dishare WA/FB/IG) -->
  <meta property="og:title" content="Laris.AI — AI untuk UMKM Indonesia">
  <meta property="og:description" content="Asisten AI keuangan & stok lewat WhatsApp.">
  <meta property="og:image" content="https://larisai.id/og-image.png">
  <meta property="og:url" content="https://larisai.id/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
```

### 2. Konten & kata kunci

- Tentukan **kata kunci utama** (riset di Google Keyword Planner / Ubersuggest):
mis. "aplikasi kasir WhatsApp", "pencatatan keuangan UMKM", "laporan KUR".
- 1 halaman = 1 kata kunci utama. Pakai di **title, H1, paragraf pertama, URL**.
- Tambah halaman pendukung (blog): "Cara catat keuangan warung", "Syarat KUR 2026",
dll. Konten panjang & bermanfaat = ranking lebih baik.

### 3. Data terstruktur (rich result)

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Laris.AI",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web, WhatsApp",
  "offers": {"@type": "Offer", "price": "0", "priceCurrency": "IDR"}
}
</script>
```

### 4. `robots.txt`

```
User-agent: *
Allow: /
Sitemap: https://larisai.id/sitemap.xml
```

### 5. `sitemap.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://larisai.id/</loc><priority>1.0</priority></url>
  <url><loc>https://larisai.id/fitur</loc><priority>0.8</priority></url>
  <url><loc>https://larisai.id/harga</loc><priority>0.8</priority></url>
</urlset>
```

### 6. Daftar ke Google (langkah kunci agar muncul)

1. **Google Search Console** ([https://search.google.com/search-console](https://search.google.com/search-console)):
  - Add property `larisai.id` → verifikasi (DNS / file HTML).
  - Menu **Sitemaps** → submit `https://larisai.id/sitemap.xml`.
  - **URL Inspection** → tempel URL → **Request Indexing** (mempercepat indeks).
2. **Google Business Profile** (jika ada lokasi usaha) → muncul di Maps & lokal.
3. **Bing Webmaster Tools** (bonus, gratis).

### 7. Teknis & kecepatan (Core Web Vitals)

- Cek skor di [https://pagespeed.web.dev](https://pagespeed.web.dev) → target hijau (mobile & desktop).
- Kompres gambar (WebP), minify CSS/JS, aktifkan HTTPS + caching.
- **Mobile-friendly wajib** (mayoritas user UMKM dari HP).

### 8. Off-page (otoritas)

- Backlink: tulis artikel/PR, daftar di direktori startup, kolaborasi komunitas UMKM.
- Bagikan ke media sosial → trafik & sinyal sosial.
- Konsisten produksi konten = naik bertahap (SEO butuh waktu ~1–3 bulan).

---

## Ekspektasi Realistis

"Paling unggul / halaman 1" **tidak instan**. Yang realistis:

- **Hari 1–7:** terindeks Google (kalau Search Console + sitemap beres).
- **Minggu 2–8:** mulai muncul untuk kata kunci spesifik/brand ("Laris.AI").
- **Bulan 2–6:** naik untuk kata kunci kompetitif bila konten + backlink rutin.

**Cara tercepat tampil di atas SEKARANG:** pasang **Google Ads** (berbayar) untuk
kata kunci target sambil SEO organik bertumbuh.

---

## Checklist Cepat Go-Live

- [ ] App Streamlit ter-deploy + secrets terisi.
- [ ] WA bot ter-deploy (service_role) + webhook aktif.
- [ ] Landing page statis online di domain sendiri (HTTPS).
- [ ] Title, meta description, OG tags, canonical terpasang.
- [ ] `robots.txt` + `sitemap.xml` ada.
- [ ] Terdaftar & sitemap disubmit di Google Search Console.
- [ ] Skor PageSpeed hijau + mobile-friendly.
- [ ] (Opsional) Google Ads aktif untuk hasil cepat.