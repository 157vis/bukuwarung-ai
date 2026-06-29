# Pre-Deploy Checklist — BukuWarung-AI v1.0.0

Centang sebelum push ke Railway production.

## Kode & test

- [ ] `pytest tests/ -v` — semua pass (target 90%+)
- [ ] `pytest tests/test_integration.py` — 25+ skenario OK
- [ ] `pytest tests/test_performance.py` — response < 5 detik (mock)
- [ ] Tidak ada secret di git (`.env` di `.gitignore`)

## Environment

- [ ] `OPENROUTER_API_KEY` valid
- [ ] `SUPABASE_URL` + `SUPABASE_KEY` valid
- [ ] `FONNTE_TOKEN` valid (device connected)
- [ ] `GROQ_API_KEY` valid
- [ ] `OWNER_PHONES` diisi nomor owner
- [ ] `.env.example` sinkron dengan `config.py`

## Database

- [ ] `sql/create_otak_memories.sql` dijalankan
- [ ] `sql/create_brand_voices.sql` dijalankan
- [ ] (Opsional) tabel `orders` jika pakai Supabase orders

## Railway

- [ ] Root directory = `bukuwarung-ai`
- [ ] `Procfile` / `railway.json` ada
- [ ] `runtime.txt` = python-3.11.6
- [ ] Health check `/health` hijau
- [ ] Domain Railway di-set di Fonnte webhook

## Smoke test lokal / USB

- [ ] `pip install -r requirements.txt`
- [ ] `copy .env.example .env` + isi keys
- [ ] `python main.py` → server jalan
- [ ] `GET http://localhost:8000/health` → OK
- [ ] (Opsional) ngrok + test webhook

## Post-deploy

- [ ] Kirim WA `halo` → balasan masuk
- [ ] `GET /stats` menunjukkan `total_messages` naik
- [ ] Log Railway tanpa error berulang
