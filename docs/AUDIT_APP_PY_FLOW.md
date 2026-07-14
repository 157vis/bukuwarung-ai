# 🔍 Audit Lengkap Alur `app.py` (1038 baris)

**Tanggal Audit:** 2026-07-13
**File:** `app.py` (entry point Streamlit dashboard)
**Status:** Codebase dipanggil dari `laris-ai.streamlit.app` (Streamlit Cloud Community)

---

## 📋 Ringkasan Eksekutif

`app.py` adalah **aplikasi Streamlit multi-tenant** yang:

1. **Layanan publik** — Tampilkan landing page marketing + login
2. **Layanan dashboard** — Buku Kas, Catat Transaksi, Gudang, Laporan KUR, Pengaturan Bot
3. **AI Integration** — Terhubung ke Groq API, OpenRouter, Supabase
4. **WhatsApp Bridge** — Forward ke `bukuwarung-ai-larisai.up.railway.app` (webhook CS) & `kita-cuan-wa-bot-larisai.up.railway.app` (bot catat)

**Domain yang aktif saat ini:**
- ✅ `laris-ai.streamlit.app` (Streamlit Cloud — AKTIF, ini yang dipakai)
- ❌ `app.larisai.my.id` (Custom domain — TIDAK terhubung ke mana-mana, 404)
- ❌ `larisai.my.id` (Arah ke FastAPI JSON, BUKAN Streamlit)
- ✅ `www.larisai.my.id` (Cloudflare Pages — landing statis)

---

## 🗺️ Alur Lengkap `app.py` (Line by Line)

### **1. Imports & Constants (Line 1-35)**

```python
import streamlit as st
import pandas as pd

from brand import APP_NAME, PAGE_ICON, PAGE_TITLE, DASHBOARD_TITLE, DEMO_QUERY
from config_runtime import get_secret, require_secret
from demo_dashboard import render_demo_dashboard
from landing import render_landing
from login import show_login_page, get_current_user, logout, ensure_valid_session
from laris_core import LarisCore
from log_config import get_logger
from pengaturan_bot import render_pengaturan_bot
```

**Constants penting:**
- `SUPER_ADMIN_EMAIL = "rafihrr1@gmail.com"` (line 30) — hanya email ini yang bisa tambah/edit client
- `DEFAULT_BUKUWARUNG_URL = "https://bukuwarung-ai-larisai.up.railway.app"` (line 33) — webhook CS
- `DEFAULT_CATAT_BOT_URL = "https://kita-cuan-wa-bot-larisai.up.railway.app"` (line 34) — bot catat

### **2. Helper Functions (Line 37-234)**

- `_bot_base_urls()` (37-41) — Ambil URL webhook dari secrets
- `agent_label()` (44-45) — Format label agent
- `render_wa_sync_hint()` (48-64) — Petunjuk sinkronisasi WA
- `get_admin_core()` (67-79) — Service role untuk Super Admin
- `get_core()` (82-94) — **PENTING**: Bikin `LarisCore` dengan JWT user (RLS Supabase)
- `render_connection_status()` (97-110) — Diagnostik database
- `page_config()` (113-119) — `st.set_page_config`
- `render_header()` (122-141) — CSS hide header
- `inject_dashboard_style()` (144-212) — Theme dark glassmorphism
- `get_query_value()` (215-220) — Ambil query param
- `get_query_flag()` (223-234) — **FIXED di d20c49d**: Sekarang support `?login` (tanpa `=1`)

### **3. Render Functions (Line 237-947)**

#### **`render_home()` (237-240)**
Panggil `render_landing()` dari `landing.py` — ini yang muncul saat user BELUM login.

#### **`render_dashboard(core, user)` (243-947)**
**Menu utama yang dirender setelah login:**

| Menu | Fungsi | Trigger |
|------|--------|---------|
| `Ruang Komando` | Approval AI decisions | Admin/Logistik AI |
| `Ringkasan` | Total income/expense, grafik, Laris Score | `hero_welcome()` + `stat_card_row()` |
| `Catat Transaksi` | Form input manual | `db_insert_transaction()` |
| `Buku Kas` | List, edit, hapus, unduh CSV | `get_dashboard_data()` |
| `Laporan KUR` | Ringkasan pengajuan KUR | Aggregat income/expense |
| `⚙️ Pengaturan Bot` | Setup WA client | `render_pengaturan_bot()` |
| `Gudang` | Warehouse & inventory | `list_warehouses()` |

**Super Admin khusus (line 633-826):**
- Tambah client baru (line 658-714)
- Update 2 nomor WA (line 720-755)
- Hubungkan nomor legacy (line 758-779)
- Lihat semua client (line 782-826)

### **4. Legacy Redirect Handler (Line 950-999)**

```python
def _redirect_legacy_paths() -> None:
    """Path yang sebenarnya dilayani Cloudflare Pages (www.larisai.my.id)
    tapi user/email/share-link bisa datang ke root domain (larisai.my.id).
    Streamlit tidak handle arbitrary path, jadi pakai JS redirect di awal.
    """
    LANDING = "https://www.larisai.my.id"
    REDIRECT_PREFIXES = ("/artikel/", "/3d/", "/laris-3d/")
```

**Fungsi:** Jika user akses `larisai.my.id/artikel/...` atau `larisai.my.id/laris-3d/...`, otomatis redirect ke `www.larisai.my.id` (Cloudflare Pages) yang serve file statis.

### **5. Main Flow (Line 1002-1033)**

```python
def main() -> None:
    page_config()                              # 1003 — Set page config
    _redirect_legacy_paths()                   # 1004 — JS redirect legacy paths
    render_header()                            # 1005 — Hide Streamlit header

    # 1. Demo mode (?demo=1)
    if get_query_flag("demo"):
        st.session_state["demo_mode"] = True
        st.session_state.pop("show_login", None)

    # 2. Login mode (?login atau ?login=1)
    show_login = st.session_state.get("show_login", False) or get_query_flag("login")
    if get_query_flag("login"):
        st.session_state.pop("demo_mode", None)
        st.session_state["show_login"] = True
        show_login = True

    # 3. Render demo dashboard (jika demo mode)
    if st.session_state.get("demo_mode"):
        render_demo_dashboard()
        return

    # 4. Render login page (jika show_login)
    if show_login:
        if show_login_page():
            render_dashboard(get_core(), get_current_user())
        return

    # 5. Render dashboard (jika sudah login)
    if st.session_state.get("user"):
        if ensure_valid_session():
            render_dashboard(get_core(), get_current_user())
        else:
            st.warning("Sesi Anda telah berakhir. Silakan masuk kembali.")
            render_home()

    # 6. Render landing page (default, belum login)
    else:
        render_home()
```

---

## 🔄 Diagram Alur Keputusan

```
User buka app.py
        │
        ▼
   page_config() + redirect legacy paths
        │
        ▼
  Cek ?demo=1 query ──── Ya ──→ render_demo_dashboard() → END
        │
       Tidak
        │
        ▼
  Cek ?login query ──── Ya ──→ show_login_page()
        │                         │
       Tidak                     ▼
        │                  Login sukses?
        ▼                    │      │
  user di session?         Ya     Tidak
        │                   │      │
       Ya                  ▼      ▼
        │            render_dashboard()  return
        ▼                   │
  ensure_valid_session()   END
        │
        ├── True → render_dashboard()
        ├── False → warning + render_home()
        │
   Tidak (belum login)
        │
        ▼
  render_home() → render_landing()
```

---

## 🔌 Integrasi External Service

### **A. Supabase (via LarisCore)**

| Aksi | Method | Tabel |
|------|--------|-------|
| Login user | `supabase.auth.sign_in_with_password()` | `auth.users` |
| Get dashboard data | `core.get_dashboard_data(user_id)` | `transactions` |
| Insert transaksi | `core.db_insert_transaction()` | `transactions` |
| Get approvals | `core.list_pending_approvals()` | `approvals` |
| Get WA messages | `core.list_wa_messages()` | `wa_messages` |
| List warehouses | `core.list_warehouses()` | `warehouses` |
| List products | `core.list_products()` | `products` |
| Link WA number | `core.link_wa_number()` | `wa_users` |
| Create client | `core.create_client_account()` | `auth.users` + `profiles` |
| Setup dual WA | `core.setup_dual_wa_client()` | `clients` + `wa_users` |

### **B. AI Service (Groq)**

| Aksi | Method |
|------|--------|
| Calculate Laris Score | `core.calculate_laris_score(df)` → Groq API |
| AI Advisor Insights | `core.get_ai_advisor_insights(df)` → Groq API |
| Chat CS (di Railway) | `https://bukuwarung-ai-larisai.up.railway.app/webhook/csat/{user_id}` |
| Catat transaksi (di Railway) | `https://kita-cuan-wa-bot-larisai.up.railway.app/webhook/catat/{user_id}` |

---

## ❓ Mengapa `app.larisai.my.id` "Tidak Terhubung"?

### **Penyebab Utama:**

1. **Domain `app.larisai.my.id` di Cloudflare DNS tidak ada CNAME yang valid**
   - Seharusnya CNAME ke Railway service Streamlit
   - Tapi **tidak ada service Streamlit di Railway** yang dideploy khusus untuk `app.larisai.my.id`

2. **Service `bukuwarung-ai-larisai` di Railway menjalankan FastAPI (BUKAN Streamlit)**
   - `main.py` adalah entry point FastAPI
   - Endpoint `/` return JSON status
   - Tidak ada `streamlit run app.py` di service ini

3. **Yang aktif saat ini adalah `laris-ai.streamlit.app` (Streamlit Cloud Community)**
   - Ini adalah deployment **terpisah** dari Railway
   - Source code di-pull dari GitHub `157vis/bukuwarung-ai` (branch `main`)
   - Auto-redeploy setiap ada push

### **Solusi yang Tersedia:**

#### **Opsi 1: Tetap Pakai `laris-ai.streamlit.app` (REKOMENDASI)**
- ✅ Sudah aktif dan stabil
- ✅ Auto-deploy dari GitHub
- ✅ Gratis
- ❌ URL panjang, bukan custom domain

#### **Opsi 2: Deploy Ulang Streamlit ke Railway**
- ✅ Custom domain `app.larisai.my.id` bisa aktif
- ❌ Railway berbayar (setelah free tier habis)
- ❌ Setup lebih ribet (Nixpacks, Procfile, port config)

#### **Opsi 3: Pakai `app.larisai.my.id` sebagai CNAME ke `laris-ai.streamlit.app`**
- ❌ **TIDAK BISA** — Streamlit Cloud tidak support custom domain (kecuali plan berbayar)
- Streamlit Community Cloud **HANYA** serve di subdomain `*.streamlit.app`

#### **Opsi 4: Front `app.larisai.my.id` dengan Cloudflare Worker**
- ✅ Redirect ke `laris-ai.streamlit.app`
- ⚠️ Bukan solusi ideal, hanya workaround
- Bisa pakai Cloudflare Rules untuk redirect

---

## ✅ Rekomendasi

### **Strategi Saat Ini (Simpel & Stabil):**

1. **Landing page** → `www.larisai.my.id` (Cloudflare Pages, statis)
   - Deploy via drag-and-drop `pages-deploy/`
   - Update CTA ke `https://laris-ai.streamlit.app/?login=1`

2. **Dashboard** → `laris-ai.streamlit.app` (Streamlit Cloud)
   - Source: GitHub `157vis/bukuwarung-ai` branch `main`
   - Auto-deploy
   - URL ini yang dipakai user untuk login

3. **Root domain** `larisai.my.id` → Redirect ke `www.larisai.my.id` (Cloudflare Rules)

4. **Custom domain `app.larisai.my.id`** → **HAPUS atau REDIRECT ke `laris-ai.streamlit.app`**
   - Tidak ada service di Railway yang handle ini
   - Lebih baik redirect ke Streamlit Cloud daripada 404

### **Aksi Konkret:**

| Task | Status | Owner |
|------|--------|-------|
| Drag-and-drop `pages-deploy/` ke Cloudflare Pages | ⏳ PENDING | User |
| Link `www.larisai.my.id` ke Pages project | ⏳ PENDING | User |
| Set Cloudflare Rule: `larisai.my.id/*` → `www.larisai.my.id` (kecuali `/webhook/*`) | ⏳ PENDING | User |
| Set Cloudflare Rule: `app.larisai.my.id/*` → `https://laris-ai.streamlit.app/?{request.uri.query}` | ⏳ PENDING | User |
| Test `www.larisai.my.id` → klik "Masuk" → landing `laris-ai.streamlit.app/?login=1` → login form | ⏳ PENDING | User |

---

## 📌 Catatan Penting

1. **`app.py` TIDAK punya route ke `app.larisai.my.id`** — Streamlit Cloud & Railway tidak saling terhubung. `app.py` adalah kode yang **dijalankan** oleh keduanya, tapi routing/URL ditentukan oleh platform yang men-deploy.

2. **`landing.py` line 25-29 sudah di-update** ke `LOGIN_URL = "https://laris-ai.streamlit.app/?login=1"` (commit 73e8c19) — semua tombol "Masuk" sekarang mengarah ke Streamlit Cloud, bukan WhatsApp.

3. **`get_query_flag()` di line 223-234 sudah di-fix** (commit d20c49d) untuk handle `?login` tanpa `=1`.

4. **Files `pages-deploy/` siap untuk drag-and-drop ke Cloudflare Pages** — berisi `index.html` (updated) + `laris-3d/` folder.
