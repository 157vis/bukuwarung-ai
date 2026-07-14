# Fix: Tabel `wa_users` Kosong → Bot Tidak Bisa Resolve

**Tanggal:** 2026-07-13
**Penyebab:** Tabel `wa_users` di Supabase kosong, sehingga `resolve_user_id_by_phone()` gagal
**Solusi:** Insert row untuk nomor HP yang akan mengirim WA

---

## ⚠️ PENTING: Saya Butuh 1 Informasi

Saya sudah tahu `user_id` toko_rafih dari `metadata`:
```
user_id: 1eaa9645-eb0d-4b85-aab8-3c6b514fa59b
```

Tinggal **nomor HP Anda** (yang akan jadi sender, berbeda dari `6285789974981`).

---

## 📋 Schema Tabel `wa_users`

Berdasarkan kode `laris_core.py:resolve_user_id_by_phone()` dan struktur Supabase:

| Kolom | Tipe | Required | Keterangan |
|-------|------|----------|------------|
| `user_id` | UUID | ✅ | Foreign key ke `auth.users.id` |
| `phone` | TEXT | ✅ | Nomor WA (format 628xxx, tanpa +) |
| `label` | TEXT | ❌ | Opsional, mis. "Test Owner" |
| `is_active` | BOOLEAN | ❌ | Default `true` |
| `created_at` | TIMESTAMPTZ | ❌ | Default `now()` |
| `updated_at` | TIMESTAMPTZ | ❌ | Default `now()` |

---

## 🚀 Cara Insert

### **Step 1: Buka Supabase SQL Editor**

1. Login ke https://supabase.com/dashboard
2. Pilih project **`tagyexrsuvogrlhcthcp`**
3. Sidebar → **SQL Editor**
4. Klik **New query**

### **Step 2: Cek struktur tabel dulu (optional safety)**

```sql
-- Cek kolom yang ada
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'wa_users'
ORDER BY ordinal_position;
```

### **Step 3: Cek apakah nomor sudah ada**

```sql
-- Ganti '6281234567890' dengan nomor Anda
SELECT * FROM wa_users WHERE phone = '6281234567890';
```

Kalau ada row → nomor sudah terdaftar, skip insert.
Kalau kosong → lanjut insert.

### **Step 4: Insert nomor Anda**

```sql
INSERT INTO wa_users (user_id, phone, label, is_active, created_at, updated_at)
VALUES (
  '1eaa9645-eb0d-4b85-aab8-3c6b514fa59b',  -- user_id toko_rafih
  'GANTI_DENGAN_NOMOR_ANDA',              -- mis. '6281234567890'
  'Test Owner',
  true,
  now(),
  now()
)
ON CONFLICT (user_id, phone) DO NOTHING    -- avoid duplicate
RETURNING *;                                -- show inserted row
```

**PENTING:** Ganti `GANTI_DENGAN_NOMOR_ANDA` dengan nomor HP Anda yang akan kirim WA.

Format yang benar:
- ✅ `6281234567890` (62 + nomor tanpa 0 di depan)
- ❌ `081234567890` (jangan pakai awalan 0)
- ❌ `+6281234567890` (jangan pakai +)

### **Step 5: Verify**

```sql
SELECT * FROM wa_users ORDER BY created_at DESC;
```

Harus muncul row baru dengan nomor Anda.

---

## 🧪 Test Setelah Insert

### **Test 1: Kirim WA "halo" ke `6285789974981`**

1. Buka WhatsApp di HP Anda
2. Chat ke nomor `6285789974981` (nomor owner toko_rafih)
3. Kirim pesan: `halo`
4. **Expected dalam ~5 detik:**
   ```
   Halo! 👋

   Aku Laris, asisten pembukuan tokomu~

   Mau catat apa hari ini?
   • jual kopi 15rb
   • beli bensin 50rb
   • utang budi 100rb

   Atau tanya: laris, gimana bisnis aku?
   ```

### **Test 2: Catat transaksi**

Kirim: `jual kopi 50rb`

**Expected:**
- Bot reply konfirmasi
- Transaksi masuk ke tabel `transactions` Supabase
- Muncul di dashboard Streamlit (menu Buku Kas)

### **Test 3: Cek log di Railway**

1. Buka https://railway.app/dashboard
2. Service `kita-cuan-wa-bot-larisai` → tab **Logs**
3. Cari log line:
   ```
   INFO FonnteClient: fonnte token resolved: phone=628xxx -> client_id=toko_rafih
   INFO fonnte send -> 200: {"status":"success",...}
   ```

---

## ❌ Kalau Masih Tidak Merespon

Cek urutan troubleshooting:

1. **Cek Fonnte webhook URL** (di dashboard Fonnte):
   ```
   https://kita-cuan-wa-bot-larisai.up.railway.app/webhook
   ```

2. **Cek device Fonnte aktif** (status harus connected, bukan disconnected)

3. **Cek log Railway** saat ada WA masuk:
   - Kalau ada log "fonnte token resolved" → token OK
   - Kalau ada log "fonnte send" → Fonnte API dipanggil
   - Kalau HTTP 500 → cek traceback error di log

4. **Cek Railway Variables**:
   - `SUPABASE_URL` ✓
   - `SUPABASE_KEY` ✓
   - `GROQ_API_KEY` ✓
   - `WA_API_KEY` (fallback, opsional)

5. **Cek Groq API**:
   - Buka https://console.groq.com
   - Pastikan key masih aktif, ada quota

---

## 🔄 Alternatif: Setup via Streamlit Dashboard

Kalau lebih suka klik-klik:

1. Buka https://www.larisai.my.id → klik **Masuk Akun**
2. Login sebagai `rafihrr1@gmail.com` (admin)
3. Menu **⚙️ Pengaturan Bot** → scroll ke **Panel Super Admin**
4. Pilih form **"Hubungkan Nomor WA (satu nomor / legacy)"**
5. Isi:
   - **User ID Client**: `1eaa9645-eb0d-4b85-aab8-3c6b514fa59b`
   - **Nomor WhatsApp**: nomor HP Anda
   - **Label**: bebas
6. Klik **Hubungkan**
7. Selesai

---

## 📝 Referensi

- Kode resolver: `laris_core.py:resolve_user_id_by_phone()` line 369
- Tabel schema: tabel `wa_users` di Supabase
- Nomor owner: ada di `clients.owner_phones` (toko_rafih = `['6285789974981']`)
