# Panduan Publish Website + SEO Google untuk laris.AI

Dokumen ini mengikuti arsitektur yang paling aman untuk SEO:

- `site/` = landing page statis untuk marketing dan indexing Google
- `app.py` = dashboard Streamlit untuk login dan operasional
- bot WhatsApp = deploy terpisah dari dashboard

## 1. Struktur file yang sudah disiapkan

Folder statis untuk landing page ada di:

- `site/index.html`
- `site/fitur/index.html`
- `site/harga/index.html`
- `site/artikel/cara-mencatat-keuangan-warung/index.html`
- `site/artikel/syarat-kur-umkm-2026/index.html`
- `site/artikel/aplikasi-kasir-whatsapp-umkm/index.html`
- `site/artikel/pembukuan-sederhana-usaha-rumahan/index.html`
- `site/artikel/cara-menghitung-laba-warung/index.html`
- `site/artikel/aplikasi-stok-barang-umkm/index.html`
- `site/artikel/contoh-catatan-pemasukan-pengeluaran-umkm/index.html`
- `site/artikel/aplikasi-kasir-toko-kelontong/index.html`
- `site/robots.txt`
- `site/sitemap.xml`
- `site/og-image.svg`

Konfigurasi Streamlit yang sudah disiapkan:

- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`

Halaman-halaman ini sudah memuat:

- title dan meta description
- canonical URL
- Open Graph tags
- robots directives
- sitemap XML
- data terstruktur JSON-LD
- internal linking antar halaman
- CTA ke dashboard: `https://app.larisai.id/?login=1`

## 2. Publish dashboard Streamlit

### Opsi cepat: Streamlit Community Cloud

1. Push repo ini ke GitHub.
2. Buka <https://share.streamlit.io>.
3. Pilih repo, branch, dan file `app.py`.
4. Masukkan secrets yang sama dengan kebutuhan aplikasi:

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "anon-key"
GROQ_API_KEY = "gsk_xxx"
```

Template yang sama juga sudah tersedia di:

```text
.streamlit/secrets.toml.example
```

5. Deploy dan dapatkan URL aplikasi.
6. Jika memakai domain sendiri, arahkan ke `app.larisai.id`.

### Opsi kontrol penuh: VPS / Railway / Render

Gunakan perintah berikut:

```bash
python -m streamlit run app.py --server.port 8501 --server.headless true
```

Lalu pasang reverse proxy dan HTTPS ke domain aplikasi, misalnya:

- `app.larisai.id` -> dashboard Streamlit

## 3. Publish landing page statis

Landing page SEO jangan di-host dari Streamlit. Host folder `site/` sebagai website statis.

### Vercel

Konfigurasi yang disarankan:

- Framework preset: `Other`
- Root directory: repository root
- Build command: kosong
- Output directory: `site`

### Netlify

Konfigurasi yang disarankan:

- Base directory: kosong
- Build command: kosong
- Publish directory: `site`

### Cloudflare Pages

Konfigurasi yang disarankan:

- Build command: kosong
- Build output directory: `site`

## 4. Domain dan DNS

Rekomendasi struktur domain:

- `https://larisai.id` -> landing page statis
- `https://app.larisai.id` -> dashboard Streamlit

Jika domain final berbeda, ubah string berikut di file statis:

- `https://larisai.id`
- `https://app.larisai.id/?login=1`

File yang biasanya perlu disesuaikan:

- `site/index.html`
- `site/fitur/index.html`
- `site/harga/index.html`
- `site/robots.txt`
- `site/sitemap.xml`

## 5. Publish bot WhatsApp

Deploy bot WhatsApp secara terpisah dari Streamlit.

Checklist umum:

- gunakan `SUPABASE_KEY = service_role` untuk proses server-side yang memang memerlukannya
- pasang webhook publik
- daftarkan webhook ke provider WhatsApp seperti Fonnte atau Wablas

Pisahkan bot dari dashboard agar scaling dan keamanan lebih rapi.

## 6. Langkah SEO setelah website online

### Google Search Console

1. Tambahkan properti domain `larisai.id`.
2. Verifikasi melalui DNS atau metode yang tersedia.
3. Submit sitemap:

```text
https://larisai.id/sitemap.xml
```

4. Gunakan menu URL Inspection untuk:
   - `https://larisai.id/`
   - `https://larisai.id/fitur/`
   - `https://larisai.id/harga/`

### Bing Webmaster Tools

Submit domain dan sitemap yang sama sebagai tambahan trafik organik.

## 7. Keyword intent yang sudah ditargetkan

Landing page ini disiapkan untuk intent:

- `AI kasir WhatsApp UMKM`
- `pencatatan keuangan WhatsApp`
- `aplikasi kasir WhatsApp`
- `laporan KUR UMKM`
- `laris.AI`

Pembagian intent halaman:

- `site/index.html` -> keyword utama brand + AI kasir WhatsApp UMKM
- `site/fitur/index.html` -> fitur dan use case
- `site/harga/index.html` -> intent harga
- `site/artikel/cara-mencatat-keuangan-warung/index.html` -> intent informasional warung / toko kecil
- `site/artikel/syarat-kur-umkm-2026/index.html` -> intent informasional pembiayaan / KUR
- `site/artikel/aplikasi-kasir-whatsapp-umkm/index.html` -> intent komersial aplikasi kasir WhatsApp
- `site/artikel/pembukuan-sederhana-usaha-rumahan/index.html` -> intent informasional usaha rumahan
- `site/artikel/cara-menghitung-laba-warung/index.html` -> intent informasional owner warung
- `site/artikel/aplikasi-stok-barang-umkm/index.html` -> intent operasional stok / inventaris
- `site/artikel/contoh-catatan-pemasukan-pengeluaran-umkm/index.html` -> intent edukatif pembukuan sederhana
- `site/artikel/aplikasi-kasir-toko-kelontong/index.html` -> intent komersial toko kelontong / retail kecil

## 8. Checklist go-live

- [ ] Dashboard Streamlit sudah ter-deploy
- [ ] Secrets Streamlit sudah terisi
- [ ] Landing page statis `site/` sudah online di domain utama
- [ ] `robots.txt` dan `sitemap.xml` bisa diakses publik
- [ ] `app.larisai.id` mengarah ke dashboard
- [ ] Sitemap sudah disubmit ke Google Search Console
- [ ] URL utama sudah di-request indexing
- [ ] Meta title, description, dan OG image sudah sesuai brand final
- [ ] Jika perlu, ganti `og-image.svg` dengan PNG final brand

## 9. Catatan SEO penting

- Streamlit tetap boleh dipakai untuk dashboard, tetapi jangan dijadikan halaman utama marketing.
- Landing page statis lebih mudah dirayapi Google dibanding komponen HTML di dalam aplikasi Streamlit.
- Ranking halaman 1 tidak instan; langkah paling penting adalah indexing cepat, konten relevan, internal link yang rapi, dan promosi berkelanjutan.
