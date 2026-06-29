# BukuWarung-AI v1.0.0

Sistem AI **multi-agent** untuk WhatsApp Customer Service UMKM Indonesia.  
Portable — bisa jalan dari laptop, USB flashdisk, atau cloud (Railway).

```
Pesan WA → Fonnte Webhook → FastAPI → Orchestrator
                ↓
         SemanticRouter → 6 Agent Spesialis
                ↓
         PersonalityEngine → Balasan WA
                ↑
            OtakAI (memory + learning)
```

## Fitur utama

| Komponen | Fungsi |
|----------|--------|
| **6 Agent** | CS, Sales, Order, Payment, Support, Admin |
| **OtakAI** | Memory jangka panjang, semantic search, feedback learning |
| **Personality** | 6 brand voice (ramah, formal, Jawa, Sunda, dll.) |
| **Semantic Router** | Rule-based + LLM fallback, route cache |
| **Orchestrator** | Pipeline lengkap + edge cases (klarifikasi, eskalasi) |
| **Fonnte** | Kirim pesan, gambar, tombol WA |

## Quick start (lokal / USB)

```powershell
cd bukuwarung-ai
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
# Edit .env — isi API keys
python main.py
```

Buka: http://localhost:8000/health

### Smoke test otomatis

```powershell
.\scripts\smoke_test.ps1
```

## Environment variables

Salin `.env.example` → `.env`. Variabel wajib:

| Variable | Deskripsi |
|----------|-----------|
| `OPENROUTER_API_KEY` | LLM chat (OpenRouter) |
| `SUPABASE_URL` / `SUPABASE_KEY` | Database memory & brand |
| `FONNTE_TOKEN` | Kirim balasan WhatsApp |
| `GROQ_API_KEY` | Embedding untuk OtakAI |
| `OWNER_PHONES` | Nomor WA owner (AdminAgent) |

Opsional: `PRIMARY_MODEL`, `BACKUP_MODEL`, `FREE_MODEL`, `HOST`, `PORT`, `APP_NAME`, `DEBUG`.

## API endpoints

| Method | Path | Fungsi |
|--------|------|--------|
| GET | `/health` | Health check |
| GET | `/stats` | Statistik pesan & agent usage |
| POST | `/webhook-whatsapp` | Webhook Fonnte (production) |
| POST | `/webhook` | Alias backward-compatible |
| POST | `/feedback` | Feedback 👍/👎 → OtakAI learning |

### Contoh webhook Fonnte

```json
POST /webhook-whatsapp
{
  "sender": "6281234567890",
  "message": "halo, mau pesan kopi",
  "client_id": "toko_berkah"
}
```

## Connect Fonnte

1. Login [fonnte.com](https://fonnte.com) → hubungkan device WA
2. Set **Webhook URL**: `https://<domain-anda>/webhook-whatsapp`
3. Method: **POST**
4. Test kirim pesan dari HP

### Test lokal dengan ngrok

```powershell
# Terminal 1
python main.py

# Terminal 2
ngrok http 8000
# Copy URL ngrok → paste di Fonnte webhook
```

## Deploy ke Railway

1. Push repo ke GitHub
2. Railway → New Project → Deploy from repo
3. Set **Root Directory** = `bukuwarung-ai` (jika monorepo)
4. Tambahkan semua env vars dari `.env.example`
5. Generate domain → set di Fonnte

Detail: [docs/DEPLOY_RAILWAY.md](docs/DEPLOY_RAILWAY.md)  
Checklist: [docs/PRE_DEPLOY_CHECKLIST.md](docs/PRE_DEPLOY_CHECKLIST.md)

File deploy:
- `Procfile` — start command uvicorn
- `railway.json` — health check `/health`
- `runtime.txt` — Python 3.11.6

## Testing

```powershell
pytest tests/ -v
pytest tests/test_integration.py -v   # 25+ skenario real
pytest tests/test_performance.py -v # response time < 5s
```

Target: **90%+ pass** (saat ini 100+ tests).

## Struktur project

```
bukuwarung-ai/
├── main.py                 # FastAPI v1.0.0
├── orchestrator.py         # Main coordinator
├── config.py               # Settings portable
├── agents/                 # 6 specialist agents
├── core/
│   ├── otak_ai.py
│   ├── personality.py
│   └── semantic_router.py
├── utils/
│   ├── openrouter.py       # LLM + token tracking
│   ├── whatsapp.py         # Fonnte integration
│   └── embeddings.py
├── data/                   # products.json, payment_methods.json
├── sql/                    # Supabase migrations
├── tests/                  # Unit + integration + performance
├── docs/                   # Deploy & checklist
└── scripts/smoke_test.ps1
```

## Agent spesialis

| Agent | Intent | Contoh |
|-------|--------|--------|
| CS | sapaan, info umum | "jam buka?" |
| Sales | harga, promo, stok | "rekomendasi produk" |
| Order | pesan, track, batal | "pesan kopi 2" |
| Payment | transfer, QRIS | "mau bayar" |
| Support | komplain, error | "aplikasi error" |
| Admin | laporan owner | "laporan omzet" |

## Troubleshooting

| Gejala | Penyebab | Solusi |
|--------|----------|--------|
| `/health` gagal | Server tidak jalan | `python main.py`, cek port 8000 |
| WA tidak dibalas | Webhook / token | Cek Fonnte URL & `FONNTE_TOKEN` |
| Balasan generic/error | LLM key | Cek `OPENROUTER_API_KEY`, lihat log |
| Memory tidak tersimpan | Supabase | Jalankan SQL, cek `SUPABASE_*` |
| Admin ditolak | Bukan owner | Tambah nomor di `OWNER_PHONES` |
| Response lambat (>5s) | LLM timeout | Router pakai rules dulu; set backup model |
| Rate limit OpenRouter | Banyak request | Auto fallback ke `BACKUP_MODEL` / `FREE_MODEL` |

## Performance

- Target response: **< 5 detik** per pesan
- Rule-based routing menghindari LLM untuk intent jelas
- Route cache (256 entri) untuk pesan berulang
- Token usage dilacak di `OpenRouterClient.session_usage`

## Kontribusi

1. Fork repo → branch fitur
2. `pytest tests/` harus pass
3. PR dengan deskripsi perubahan
4. Ikuti pola agent: inherit `BaseAgent`, implement `process()`

## Lisensi

Proyek internal UMKM — hubungi maintainer untuk penggunaan komersial.

---

**v1.0.0** — Multi-agent WhatsApp CS siap production (Railway + portable USB).
