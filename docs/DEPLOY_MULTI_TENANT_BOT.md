# Panduan Deploy Refactor Multi-Tenant Bot Catat

**Tanggal:** 2026-07-13
**Target:** Deploy FonnteClient multi-tenant ke Railway production
**Waktu:** ~5 menit total

---

## Latar Belakang

Bot Catat (`kita-cuan-wa-bot-larisai`) saat ini masih pakai kode LAMA:
- `WA_API_KEY` single token di env (satu nomor untuk semua client)
- Tidak scalable untuk multi-toko

Refactor sudah selesai di **monorepo** `157vis/bukuwarung-ai` (commit `94640ad`):
- `fonnte_client.py` BARU — lookup `fonnte_token` per phone dari Supabase
- `main.py` refactored — pakai FonnteClient, fallback ke env
- Multi-tenant: setiap toko bisa punya Fonnte device sendiri

Bot production running di **repo terpisah** `157vis/kita-cuan-wa-bot`.
Patch script `apply-patch.ps1` sudah disiapkan untuk copy file otomatis.

---

## Langkah-Langkah

### **Step 1: Buka PowerShell di folder monorepo**

Buka Windows PowerShell (atau Terminal), lalu:

```powershell
cd "C:\Users\Teknik SAP MTAL\bukuwarungai"
```

### **Step 2: Dry run dulu (cek apa yang akan di-copy)**

```powershell
.\kita-cuan-wa-bot-patch\apply-patch.ps1 -DryRun
```

**Expected output:**
```
=== DRY RUN - tidak ada perubahan yang dilakukan ===

Patch files yang akan di-copy:
  - main.py (exists/missing in repo, source: 5340 bytes)
  - fonnte_client.py (missing in repo, source: 5400 bytes)
  - railway.toml (exists in repo, source: 250 bytes)
  - README.md (exists in repo, source: 3500 bytes)
```

Kalau `fonnte_client.py` statusnya `missing in repo` → aman, file baru akan ditambah.

### **Step 3: Apply patch + auto-push**

```powershell
.\kita-cuan-wa-bot-patch\apply-patch.ps1 -AutoPush
```

**Expected output:**
```
[1/4] Backup file lama...
  [BAK] C:\...\Projects\kita-cuan-wa-bot\main.py.bak-20260713-xxxxxx
  [BAK] C:\...\Projects\kita-cuan-wa-bot\railway.toml.bak-20260713-xxxxxx

[2/4] Copy file patched...
  [COPY] main.py (5340 bytes)
  [COPY] fonnte_client.py (5400 bytes)
  [COPY] railway.toml (250 bytes)
  [COPY] README.md (3500 bytes)

[3/4] Preview diff...
  main.py        | 50 ++++++++++++++---------
  fonnte_client.py | 200 +++++++++++++++++++++++++++++++
  railway.toml   | 0
  README.md      | 0

[4/4] Commit...
  Commit OK

[5/5] Push ke origin main...
  Push OK

=== SELESAI - PATCH SUDAH DI-PUSH ===
```

### **Step 4: Railway auto-redeploy**

Railway akan otomatis detect push ke GitHub dan mulai build.

Buka https://railway.app/dashboard → service `kita-cuan-wa-bot-larisai` → tab **Deployments**.

Tunggu ~2-4 menit sampai status "Success".

### **Step 5: Verifikasi refactor aktif**

Buka di browser atau curl:

```
https://kita-cuan-wa-bot-larisai.up.railway.app/health
```

**Expected response (BARU — ada 2 field tambahan):**
```json
{
  "status": "ok",
  "service": "laris.AI WhatsApp Bot",
  "provider": "fonnte",
  "missing_env": [],
  "env_token_fallback": false,
  "token_source": "supabase_per_client",
  "bot_logic_version": "2026-06-28-portable-v6"
}
```

**Field pembeda:**
- `env_token_fallback` → `false` artinya tidak pakai env WA_API_KEY
- `token_source` → `"supabase_per_client"` artinya lookup dari Supabase

Kalau 2 field ini **muncul** → refactor SUDAH AKTIF ✅
Kalau 2 field ini **tidak ada** → masih kode lama, tunggu build lagi

### **Step 6: Test end-to-end**

#### Test 1: Kirim teks biasa
Dari HP, kirim WA ke `6285789974981` (nomor owner `toko_rafih` di Supabase):

```
halo
```

**Expected:** Bot reply "Halo! Aku Laris..." via Fonnte device toko_rafih.

#### Test 2: Catat transaksi
Kirim WA:
```
jual kopi 50rb
```

**Expected:**
- Bot reply konfirmasi
- Transaksi masuk ke Supabase `transactions` table
- Muncul di dashboard Streamlit `laris-ai.streamlit.app`

#### Test 3: Cek Railway logs
Buka Railway dashboard → service → tab **Logs**.

**Expected log lines:**
```
INFO FonnteClient: fonnte token resolved: phone=6285789974981 -> client_id=toko_rafih
INFO fonnte send -> 200: {"status":"success"}
```

---

## Troubleshooting

### "Repo path tidak ditemukan"

Pastikan folder `C:\Users\Teknik SAP MTAL\Projects\kita-cuan-wa-bot` ada dan berisi git repo.

```powershell
Test-Path "C:\Users\Teknik SAP MTAL\Projects\kita-cuan-wa-bot"
# True
```

Kalau belum ada, clone dulu:
```powershell
git clone https://github.com/157vis/kita-cuan-wa-bot.git "C:\Users\Teknik SAP MTAL\Projects\kita-cuan-wa-bot"
```

### "git push gagal"

Pastikan credentials GitHub sudah diset:
- HTTPS: Personal Access Token (PAT) di Windows Credential Manager
- SSH: `ssh-add` dengan key yang sudah di-add ke GitHub

Test:
```powershell
git -C "C:\Users\Teknik SAP MTAL\Projects\kita-cuan-wa-bot" push origin main
```

### Build Railway gagal

Cek tab **Logs** di Railway. Kemungkinan:
- Missing `fonnte_client.py` di repo → ulangi Step 3
- Python version mismatch → cek `runtime.txt` atau `railway.toml`

### Test WA tidak terkirim

Cek Railway logs:
- `fonnte token resolved` → token ditemukan ✅
- `send_message: tidak ada fonnte_token` → token kosong untuk phone tsb

Kalau token kosong, pastikan nomor owner ada di tabel `clients.owner_phones` Supabase.

---

## Rollback (kalau ada masalah)

```powershell
# Restore backup
$repoPath = "C:\Users\Teknik SAP MTAL\Projects\kita-cuan-wa-bot"
$latestBak = Get-ChildItem "$repoPath\*.bak-*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Copy-Item $latestBak.FullName "$repoPath\main.py" -Force
cd $repoPath
git add main.py
git commit -m "rollback: restore previous main.py"
git push origin main
```

Atau di Railway: tab **Deployments** → klik deployment sebelumnya → **Redeploy**.

---

## Setelah Sukses

1. ✅ Test multi-tenant works
2. (Opsional) Hapus `WA_API_KEY` dari Railway Variables (kalau tidak perlu fallback)
3. Update `docs/PANDUAN_RAILWAY.md` di monorepo (tandai `token_source = supabase`)
4. Commit & push di monorepo: `docs: mark bot as multi-tenant`

---

## Referensi

- Source refactor: monorepo commit `94640ad` (`fonnte_client.py` + `main.py` refactored)
- Patch script: `kita-cuan-wa-bot-patch/apply-patch.ps1`
- Test: `python -c "from kita_cuan_wa_bot_patch.fonnte_client import FonnteClient; ..."`
- Supabase schema: tabel `clients` dengan kolom `fonnte_token`, `owner_phones`
