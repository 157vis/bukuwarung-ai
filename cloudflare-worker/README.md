# Cloudflare Worker - Streamlit Proxy

Worker ini forward semua request dari `larisai.my.id` ke `laris-ai.streamlit.app` (Streamlit Cloud).

## Fitur

- ✅ Support WebSocket (Streamlit butuh ini untuk real-time)
- ✅ Rewrite HTML/JS agar tidak redirect ke `streamlit.app`
- ✅ Hapus header CSP/X-Frame-Options yang memblokir
- ✅ Handle redirect 301/302/307/308 (ganti tujuan balik ke domain kita)
- ✅ Auto-deploy dari GitHub

## Setup (5 menit, sekali)

### 1. Push ke GitHub

Pastikan folder `cloudflare-worker/` ter-push ke repo `157vis/bukuwarung-ai`.

### 2. Connect ke Cloudflare

1. Buka **https://dash.cloudflare.com**
2. **Workers & Pages** → **Create application** → **Create Worker**
3. Pilih tab **"Import a repository"**
4. Pilih **GitHub account** → repo `157vis/bukuwarung-ai`
5. **Project name**: `larisai-proxy`
6. **Build command**: (kosong)
7. **Deploy command**: (kosong)
8. Klik **Deploy**
9. Tunggu 1-2 menit sampai deploy selesai

### 3. Setup Custom Domain

1. Di project `larisai-proxy` → tab **Settings** → **Triggers** → **Custom Domains**
2. Klik **Add Custom Domain**
3. Tambah:
   - `larisai.my.id` (root)
   - `www.larisai.my.id` (www)
4. Cloudflare otomatis buat CNAME record di DNS
5. Tunggu 2-5 menit propagasi

### 4. Test

Buka `https://larisai.my.id` di browser. Harus muncul Streamlit dashboard.

## Auto-Deploy

Setiap push ke branch `main` di folder `cloudflare-worker/` = auto-deploy.

Atau pakai GitHub Actions (lihat `.github/workflows/deploy-worker.yml`).

## Troubleshooting

### Worker tidak respond
- Cek tab **Logs** di project `larisai-proxy` untuk error
- Pastikan deployment berhasil (tidak ada error build)

### WebSocket tidak jalan (Streamlit freeze)
- Pastikan Cloudflare account Anda support WebSocket (semua plan support)
- Cek `/_stcore/stream` — harus return 101 Switching Protocols

### Streamlit redirect ke laris-ai.streamlit.app
- Refresh browser dengan **hard reload** (Ctrl+Shift+R)
- Clear browser cache
