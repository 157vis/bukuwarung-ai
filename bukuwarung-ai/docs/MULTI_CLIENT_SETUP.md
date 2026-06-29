# Setup Multi-Client — Banyak Toko, Satu Railway

Satu deploy BukuWarung-AI bisa melayani **puluhan/ratusan UMKM** (multi-tenant). Setiap toko punya identitas terpisah: produk, pembayaran, personality, Fonnte token, dan memory pelanggan.

## Arsitektur

```
                    ┌─────────────────────────────────┐
                    │   Railway (1 instance)          │
                    │   bukuwarung-ai.up.railway.app  │
                    └───────────────┬─────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
 /webhook-whatsapp/          /webhook-whatsapp/          /webhook-whatsapp/
   toko_berkah                  toko_segar                  toko_makmur
        │                           │                           │
   Fonnte #1                   Fonnte #2                   Fonnte #3
   WA Warung Berkah             WA Toko Segar               WA Toko Makmur
```

**Isolasi per client:**
| Data | Kunci isolasi |
|------|----------------|
| Memory OtakAI | `{client_id}:{nomor_wa}` |
| Brand voice | `brand_voices.client_id` |
| Produk & payment | `clients.products` / `clients.payment_methods` |
| Owner admin | `clients.owner_phones` |
| Balasan WA | `clients.fonnte_token` |

---

## Opsi A: Supabase (production, banyak client)

### 1. Jalankan SQL

Di Supabase SQL Editor, jalankan berurutan:

1. `sql/create_otak_memories.sql`
2. `sql/create_brand_voices.sql`
3. `sql/create_clients.sql`

### 2. Onboarding client baru

```sql
insert into clients (
  client_id,
  name,
  fonnte_token,
  owner_phones,
  profile_key,
  products,
  payment_methods
) values (
  'toko_berkah',
  'Warung Berkah',
  'TOKEN_FONNTE_DEVICE_WARUNG_BERKAH',
  array['6281234567890'],
  'ramah_warm',
  '[
    {"name":"kopi","price":3500,"stock":50},
    {"name":"indomie","price":3500,"stock":20}
  ]'::jsonb,
  '[
    {"bank":"BCA","account_number":"1234567890","account_name":"Warung Berkah","type":"transfer"}
  ]'::jsonb
);
```

**Profile key tersedia:** `ramah_warm`, `formal_pro`, `santai_kids`, `sunda_asli`, `jawa_ngoko`, `jawa_krama`

### 3. Fonnte per client

Di dashboard Fonnte device client:

| Setting | Nilai |
|---------|-------|
| Webhook URL | `https://<railway-domain>/webhook-whatsapp/toko_berkah` |
| Method | POST |

> Ganti `toko_berkah` dengan `client_id` yang sama di database.

### 4. Verifikasi

```bash
curl https://<domain>/clients
curl https://<domain>/health
```

Kirim WA ke nomor client → harus dapat balasan dengan produk client tersebut.

---

## Opsi B: File JSON (USB / staging / < 10 client)

### 1. Salin template

```powershell
copy data\clients.example.json data\clients.json
```

### 2. Edit `data/clients.json`

```json
{
  "toko_berkah": {
    "name": "Warung Berkah",
    "fonnte_token": "TOKEN_FONNTE_1",
    "owner_phones": ["6281234567890"],
    "profile_key": "ramah_warm",
    "products": [...],
    "payment_methods": [...],
    "is_active": true
  },
  "toko_segar": {
    "name": "Toko Segar",
    "fonnte_token": "TOKEN_FONNTE_2",
    ...
  }
}
```

### 3. Webhook Fonnte

Setiap device → URL berbeda:
- `https://<domain>/webhook-whatsapp/toko_berkah`
- `https://<domain>/webhook-whatsapp/toko_segar`

---

## Skala: berapa client per deploy?

| Jumlah client | Rekomendasi |
|---------------|-------------|
| 1–10 | 1 Railway instance, JSON atau Supabase |
| 10–100 | Supabase `clients` table, monitor `/stats` |
| 100+ | Pertimbangkan Railway horizontal scaling + Redis cache |

**Tips performa:**
- Rule-based routing menghindari LLM untuk 80%+ pesan
- Route cache aktif untuk pesan berulang
- Satu `OPENROUTER_API_KEY` dipakai semua client (billing terpusat)

---

## Checklist onboarding client baru

1. [ ] Buat `client_id` unik (slug: `toko_nama`, tanpa spasi)
2. [ ] Insert ke Supabase `clients` ATAU tambah ke `data/clients.json`
3. [ ] Isi `fonnte_token` device WA client
4. [ ] Isi `owner_phones` untuk akses AdminAgent
5. [ ] Isi `products` + `payment_methods`
6. [ ] Pilih `profile_key` brand voice
7. [ ] Set Fonnte webhook → `/webhook-whatsapp/{client_id}`
8. [ ] Test: kirim `halo` dari WA client
9. [ ] Test owner: kirim `laporan harian` dari nomor owner
10. [ ] (Opsional) Insert `brand_voices` untuk override lanjutan

---

## Nonaktifkan client

```sql
update clients set is_active = false where client_id = 'toko_lama';
```

Atau di JSON: `"is_active": false`

Webhook akan return HTTP 404 — pesan tidak diproses.

---

## Troubleshooting multi-client

| Masalah | Penyebab | Solusi |
|---------|----------|--------|
| 404 Client tidak ditemukan | `client_id` di URL salah | Cek `/clients`, samakan slug |
| Balasan pakai produk client lain | Memory tidak terisolasi | Pastikan deploy v1.0.1+ (memory scope) |
| WA tidak terkirim | Token salah | Cek `fonnte_token` per client |
| Admin ditolak | Owner salah | Cek `owner_phones` di clients |
| Semua client pakai token sama | Legacy webhook | Pakai URL `/webhook-whatsapp/{client_id}` |

---

## Railway: env vars (satu untuk semua client)

Env di Railway **tidak perlu** diulang per client. Cukup:

```
OPENROUTER_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
GROQ_API_KEY=...
```

`FONNTE_TOKEN` global opsional (fallback). **Per client** token disimpan di tabel `clients`.

Lihat juga: [DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md)
