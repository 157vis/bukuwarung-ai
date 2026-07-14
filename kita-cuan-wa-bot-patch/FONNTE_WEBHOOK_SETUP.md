# PANDUAN SETUP WEBHOOK FONNTE → kita-cuan-wa-bot

Bot WhatsApp `kita-cuan-wa-bot-larisai.up.railway.app` sudah berjalan dan
endpoint `/webhook` siap menerima POST dari Fonnte.

## Status Patch (per Juli 2026)

| Patch | Commit | Perbaikan |
|---|---|---|
| v1 | `1c27f0f` | lazy Groq init + `/health` endpoint + V2 railway.toml |
| v2 | `27b2dc6` | fix `NameError: _is_outgoing_or_bot_echo` di webhook handler |
| v3 | `c0aa7d8` | **MULTI-TENANT** — `FonnteClient` lookup token per phone dari Supabase `clients` |
| v4 | `03bb459` | fix `NameError: get_core` + global exception handler |

**Test webhook** (sudah diverifikasi 2026-07-13):
```
POST /webhook {"member":"6282112826851","message":"halo"}
→ HTTP 200 {"status":"ok","mode":"ping","wa_logged":true}
```

**Mode multi-tenant aktif**: token Fonnte di-resolve per nomor dari tabel `clients` di Supabase. Bot **TIDAK LAGI** pakai `WA_API_KEY` dari Railway.

**Yang perlu Anda lakukan**: **daftarkan URL webhook di dashboard Fonnte** (atau via API).

---

## URL Webhook (paste persis)

```
https://kita-cuan-wa-bot-larisai.up.railway.app/webhook
```

Verifikasi cepat: buka URL di browser. Response harus:
```json
{"status":"webhook_ready","provider":"fonnte","bot_name":"Laris","bot_logic_version":"2026-06-28-portable-v6","hint":"POST dari Fonnte ke URL ini"}
```

---

## Cara 1: Via Dashboard Fonnte (RECOMMENDED)

1. Login ke https://md.fonnte.com
2. Pilih **device** Anda (nomor WhatsApp yang sudah connect)
3. Klik **Edit** (atau ikon pensil)
4. Isi field:
   - **Webhook**: `https://kita-cuan-wa-bot-larisai.up.railway.app/webhook`
   - **Autoread**: `ON` ⚠️ **WAJIB!** Kalau OFF, webhook tidak kirim pesan
5. Klik **Simpan / Save**
6. Test: kirim pesan WhatsApp ke nomor device Anda dari HP lain

---

## Cara 2: Via API Fonnte (otomatis)

```bash
curl -X POST https://api.fonnte.com/update-device \
  -H "Authorization: <WA_API_KEY_ANDA>" \
  -F "device=<NOMOR_DEVICE>" \
  -F "webhook=https://kita-cuan-wa-bot-larisai.up.railway.app/webhook" \
  -F "autoread=true" \
  -F "personal=true" \
  -F "group=true"
```

Ganti:
- `<WA_API_KEY_ANDA>` = token dari dashboard Fonnte (sama dengan `WA_API_KEY` di Railway)
- `<NOMOR_DEVICE>` = nomor WhatsApp device, mis. `6282112826851`

Response sukses:
```json
{"status":true,"reason":"device updated"}
```

---

## Cara 3: Test Manual (cek bot hidup)

Setelah webhook terdaftar, test dengan kirim pesan ke nomor WhatsApp Anda:

| Test | Pesan | Expected Reply |
|---|---|---|
| Test 1 (ping) | `halo` | "Halo! 👋 Aku Laris, asisten pembukuan tokomu~ Mau catat apa hari ini?" |
| Test 2 (jual) | `jual kopi 15rb` | "✅ Tercatat: Pemasukan Rp 15.000 — Jual kopi" |
| Test 3 (beli) | `beli bensin 50rb` | "✅ Tercatat: Pengeluaran Rp 50.000 — Beli bensin" |
| Test 4 (piutang) | `utang budi 100rb` | "✅ Tercatat: Piutang Rp 100.000 — Bud" |
| Test 5 (analitik) | `Laris, gimana bisnis aku?` | "📊 Analisa bisnis kamu..." (butuh Groq) |

---

## Troubleshooting

### Pesan tidak dibalas bot

1. **Cek Autoread = ON** di Fonnte dashboard (WAJIB!).
2. **Cek webhook URL** — harus persis:
   `https://kita-cuan-wa-bot-larisai.up.railway.app/webhook`
3. **Cek log Railway** — service `kita-cuan-wa-bot-larisai` → tab **Logs**.
   Cari baris `[POST] /webhook` atau `webhook keys:`. Kalau ada, berarti Fonnte sudah kirim.
4. **Cek env var** — `WA_API_KEY` di Railway harus sama dengan token Fonnte.
5. **Test webhook lokal**:
   ```bash
   curl -X POST https://kita-cuan-wa-bot-larisai.up.railway.app/webhook \
     -H "Content-Type: application/json" \
     -d '{"device":"6282112826851","message":"halo","sender":"6281234567890","name":"Test User"}'
   ```
   Bot harus return `{"status":"reply_sent"}` atau similar.

### Bot balas "ada gangguan" / 500 error

Cek tab **Logs** di Railway untuk error spesifik. Kemungkinan:
- `SUPABASE_URL` / `SUPABASE_KEY` salah
- `GROQ_API_KEY` tidak valid / kadaluarsa
- Nomor pengirim belum terdaftar di tabel `wa_users` Supabase

### Test pakai ngrok (kalau Railway publik)

URL webhook Railway sudah publik, jadi tidak perlu ngrok. Cukup:
- Buka dashboard Fonnte
- Set webhook URL
- Test kirim pesan

---

## Verifikasi Akhir

```bash
# 1. Cek service alive
curl https://kita-cuan-wa-bot-larisai.up.railway.app/health
# Expected: {"status":"ok","missing_env":[]}

# 2. Cek webhook handler
curl https://kita-cuan-wa-bot-larisai.up.railway.app/webhook
# Expected: {"status":"webhook_ready",...}

# 3. Test POST (simulasi Fonnte)
curl -X POST https://kita-cuan-wa-bot-larisai.up.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"device":"6282112826851","message":"halo","sender":"6281234567890"}'
# Expected: {"status":"reply_sent"} atau error message jelas
```

Kalau semua ✅, bot siap dipakai untuk catat transaksi UMKM via WhatsApp.
