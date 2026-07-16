# 📚 Tutorial Pendaftaran Client Baru — laris.AI

> Panduan lengkap step-by-step untuk mendaftarkan toko/client baru ke sistem laris.AI Multi-Agent.

---

## 🎯 Overview

Sistem laris.AI Multi-Tenant memungkinkan banyak toko (client) berjalan dalam **1 aplikasi** dengan **data terisolasi per-toko**. Setiap client punya:
- Nomor WhatsApp sendiri (untuk customer chat)
- Nomor WhatsApp owner (untuk pencatatan transaksi via WA)
- Plan tier (Free / Pro / Bisnis / Kemitraan)
- Data transaksi, produk, gudang terpisah

---

## 📋 PERSIAPAN (Sebelum Daftarkan)

### Yang Perlu Disiapkan dari Calon Client:

| Data | Contoh | Wajib? |
|------|--------|--------|
| Nama toko | "Toko Sumber Rezeki" | ✅ Ya |
| Nomor WhatsApp Customer Service (CS) | 6281234567890 | ✅ Ya |
| Nomor WhatsApp Owner (untuk catat transaksi) | 6289876543210 | ✅ Ya |
| Fonnte Token CS | (dari dashboard Fonnte) | ✅ Ya |
| Fonnte Token Owner (kalau beda device) | (opsional) | ❌ Tidak |
| Email owner (untuk login Streamlit) | owner@gmail.com | ✅ Ya |
| Alamat toko (opsional) | "Jl. Sudirman No. 1" | ❌ Tidak |
| User UUID dari Supabase auth.users | (otomatis setelah daftar) | Auto |

---

## 🚀 LANGKAH PENDAFTARAN (3 Tahap)

### Tahap 1 — Owner Daftar Akun Streamlit

1. Buka `https://laris-ai.streamlit.app/`
2. Klik tombol **"Masuk"**
3. Pilih **"Sign up"** (kalau belum punya akun) atau **"Login dengan Google"**
4. Pilih email Google yang akan dijadikan akun owner
5. Streamlit otomatis simpan user ke tabel `auth.users` Supabase
6. **COPY USER UUID** dari tabel `auth.users` (lihat di Supabase Dashboard → Authentication → Users)

---

### Tahap 2 — Daftarkan Toko ke Tabel `clients`

#### Opsi A — Via Streamlit (Recommended, untuk Owner Non-Teknis)

1. Login ke Streamlit sebagai **Super Admin** (`rafihrr1@gmail.com`)
2. Buka menu **"Tambah Gudang"** (hanya muncul untuk admin)
3. Isi form:
   - **Nama Toko**: nama toko client
   - **Lokasi**: alamat toko (opsional)
   - **Catatan**: catatan tambahan (opsional)
4. Klik **"Buat Gudang"**
5. Gudang akan dibuat di tabel `warehouses`

> ⚠️ **Catatan**: Form ini BELUM otomatis insert ke `clients`. Anda tetap perlu jalankan SQL Tahap 3 di bawah untuk setup WA bot.

#### Opsi B — Via SQL Langsung (Recommended untuk Admin)

Jalankan SQL ini di **Supabase Dashboard → SQL Editor**:

```sql
INSERT INTO clients (
  client_id,
  name,
  fonnte_token,
  owner_phones,
  profile_key,
  products,
  payment_methods,
  is_active,
  metadata
) VALUES (
  'toko_sumber_rezeki',                          -- client_id (slug dari nama)
  'Toko Sumber Rezeki',                          -- nama toko
  'TOKEN_FONNTE_CS_DISINI',                      -- token Fonnte untuk CS
  ARRAY['6289876543210'],                        -- array nomor owner
  'sumber_rezeki',                               -- profile key unik
  '{"items": []}'::jsonb,                        -- products (kosong dulu)
  '{"cash": true, "transfer": true}'::jsonb,     -- metode pembayaran
  true,                                          -- is_active
  jsonb_build_object(
    'user_id', 'UUID_DARI_AUTH_USERS',           -- ⚠️ GANTI dengan UUID owner
    'wa_cs', '6281234567890',                    -- nomor WA CS
    'wa_catat', '6289876543210',                 -- nomor WA owner
    'whatsapp_display', '0812-3456-7890',        -- display CS
    'whatsapp_catat_display', '0898-7654-3210',  -- display owner
    'webhook_cs', 'https://bukuwarung-ai-larisai.up.railway.app/webhook/csat/UUID',
    'webhook_catat', 'https://bukuwarung-ai-larisai.up.railway.app/webhook/catat/UUID',
    'webhook_path', '/webhook-whatsapp/toko_sumber_rezeki',
    'pattern', 'multitenant_v1',
    'migrated_at', NOW()::text
  )
);
```

**Yang WAJIB diganti**:
- `client_id`: slug unik (huruf kecil + underscore, tanpa spasi)
- `fonnte_token`: dari dashboard Fonnte
- `user_id` di metadata: UUID dari Supabase auth.users
- `wa_cs`, `wa_catat`: nomor WA yang sudah dinormalisasi (format `62xxx`, tanpa `+` atau spasi)
- `webhook_cs`, `webhook_catat`: ganti `UUID` dengan UUID owner

---

### Tahap 3 — Setup Webhook di Fonnte Dashboard

1. Buka **https://fonnte.com** → login
2. Pilih **device** toko (CS atau Owner)
3. Masuk ke **Setting → Webhook**
4. Isi URL webhook:
   - Untuk **CS** (customer chat):
     ```
     https://kita-cuan-wa-bot-larisai.up.railway.app/webhook-whatsapp/toko_sumber_rezeki
     ```
   - Untuk **Owner** (catat transaksi):
     ```
     https://kita-cuan-wa-bot-larisai.up.railway.app/webhook-catat/toko_sumber_rezeki
     ```
5. Centang event **"Message"** (untuk chat masuk)
6. Klik **"Simpan" / "Save"**

---

### Tahap 4 — Test & Verifikasi

#### Test 1: Customer Chat (via nomor CS)

1. Dari HP lain, chat ke nomor CS toko (`0812-3456-7890`)
2. Kirim pesan: "halo"
3. **Expected**: dapat balasan otomatis dari AI CS dalam 5-10 detik
4. Cek log Railway `kita-cuan-wa-bot` → cari `ROUTE DEBUG: CUSTOMER ROUTE AKTIF`

#### Test 2: Owner Catat Transaksi (via nomor Owner)

1. Dari HP owner, chat ke nomor Owner (`0898-7654-3210`)
2. Kirim pesan: "beli indomie 5000"
3. **Expected**: AI Catat konfirmasi + simpan ke database
4. Buka Streamlit → menu **Ruang Komando** → harusnya ada approval pending

#### Test 3: Login ke Streamlit

1. Owner login ke `laris-ai.streamlit.app` dengan emailnya
2. Buka menu **Ruang Komando**
3. Cek banner plan tier — untuk Free akan ada banner kuning

---

## 🔧 TROUBLESHOOTING UMUM

### ❌ Customer chat tidak dibalas

**Cek**:
1. Apakah `fonnte_token` di tabel `clients` valid? Test dari Postman:
   ```bash
   curl -X POST https://api.fonnte.com/send \
     -H "Authorization: TOKEN_FONNTE" \
     -d "target=6281234567890&message=test"
   ```
2. Apakah webhook URL di Fonnte benar?
3. Apakah `client_id` di tabel `clients` sama dengan di webhook URL?
4. Cek log Railway untuk error

### ❌ Owner tidak bisa catat transaksi

**Cek**:
1. Apakah nomor owner ada di `owner_phones` array? Format harus `62xxx`:
   ```sql
   SELECT owner_phones FROM clients WHERE client_id = 'toko_sumber_rezeki';
   ```
2. Apakah `user_id` di metadata sama dengan UUID Supabase auth owner?
3. Cek log Railway untuk baris `ROUTE DEBUG: phone=xxx -> resolve_user_id=xxx`

### ❌ Data toko lain bocor ke toko baru

**Cek RLS policies** di Supabase:
```sql
SELECT schemaname, tablename, policyname
FROM pg_policies
WHERE schemaname = 'public';
```

Pastikan tiap tabel (`products`, `warehouses`, `transactions`, dll) punya policy `user_id = auth.uid()`.

---

## 📊 Tabel Ringkasan Pendaftaran

| Langkah | Tujuan | Tools |
|---------|--------|-------|
| 1. Owner signup | Bikin akun Streamlit | Browser |
| 2. Insert ke `clients` | Daftarkan toko + mapping UUID | Supabase SQL Editor |
| 3. Setup webhook Fonnte | Hubungkan nomor WA → bot | Dashboard Fonnte |
| 4. Test & verify | Pastikan semua flow jalan | HP + Streamlit |

---

## 💎 Setelah Pendaftaran Sukses

1. ✅ Client bisa login ke Streamlit
2. ✅ Customer chat → dibalas AI CS Multi-Agent
3. ✅ Owner catat transaksi via WA → masuk approval
4. ✅ Data terisolasi per-toko (3 layer: app, session, RLS)
5. ✅ Bisa upgrade plan kapan saja

---

## 📞 Butuh Bantuan?

- WhatsApp Admin: 0857-8997-4981
- Lihat log Railway: `kita-cuan-wa-bot` service
- Lihat log bukuwarung-ai: `bukuwarung-ai-larisai` service