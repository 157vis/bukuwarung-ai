# Integrasi Dasher → laris.AI Dashboard

## Apa itu Dasher?

**Dasher 1.0.0** adalah template admin **Bootstrap 5** (HTML + SCSS + Gulp), bukan aplikasi Python.
Stack asli:

| Dasher | laris.AI (sekarang) |
|--------|---------------------|
| HTML / Bootstrap | **Streamlit** (`app.py`) |
| ApexCharts | `st.line_chart` / `st.bar_chart` |
| Sidebar `#miniSidebar` | `st.sidebar` + CSS `ui/laris_theme.py` |
| Sign-in HTML | `login.py` + tema Dasher |
| Data statis demo | **Supabase** + `laris_core.py` |

Kita **tidak mengganti** backend (Supabase, webhook WA, `laris_core`). Yang diserap dari Dasher: **tampilan modern** (warna, kartu, sidebar, hero).

## Yang sudah disinkronkan (v2 — tampilan Dasher asli)

- **`static/assets/dasher/theme.css`** — CSS Dasher 1.0.0 (dari zip)
- **Bootstrap 5.3 + Tabler Icons** — sama seperti template asli
- **Sidebar putih** lebar 260px, tombol menu aktif hijau (`primary-bg-subtle`)
- **Topbar** + kartu `card card-lg`, hero `bg-gradient-mixed`
- **Login** — layout `sign-in.html` (kartu putih)
- **Fungsi bisnis** — tidak berubah (`laris_core`, Supabase, semua menu)

### Menu (nama laris.AI)

| Menu | Fungsi |
|------|--------|
| 🚀 Ruang Komando | Approvals AI (Proactive UI) |
| 📊 Ringkasan | Metrik + grafik + Laris Score |
| ✏️ Catat Transaksi | Input manual |
| 💰 Buku Kas | Daftar transaksi |
| 📋 Laporan KUR | Laporan bank |
| 📦 Gudang | Inventori (jika tabel ada) |
| ⚙️ Pengaturan Bot | Token Fonnte & webhook |

## File penting

| Path | Peran |
|------|--------|
| `ui/laris_theme.py` | CSS Dasher-style untuk Streamlit |
| `ui/components.py` | Kartu hero & statistik |
| `ui/menu_config.py` | Pemetaan menu sidebar |
| `static/assets/laris/logo-icon.svg` | Logo sidebar |
| `_dasher_preview/` | Zip asli (lokal, di `.gitignore`) |

## Cara melihat hasil

```powershell
cd "C:\Users\Teknik SAP MTAL\bukuwarungai"
.\scripts\run-dashboard.ps1
```

Buka `http://localhost:8501` → login → **📊 Ringkasan** (hero + kartu metrik baru).

## Langkah berikutnya (opsional)

1. **Landing page** — port halaman `index.html` Dasher ke `static/laris-landing.html` (ganti semua teks "Dasher" → laris.AI).
2. **Grafik ApexCharts** — jika ingin chart persis seperti Dasher, tambah `streamlit-apexcharts` atau embed JS component.
3. **Frontend terpisah** — build Dasher (`npm run build`) + API FastAPI (`bukuwarung-ai/main.py`) untuk tim yang ingin 100% HTML murni.

## Lisensi

Dasher: MIT (ThemeWagon / CodesCandy). Kode integrasi di folder `ui/` milik project laris.AI.
