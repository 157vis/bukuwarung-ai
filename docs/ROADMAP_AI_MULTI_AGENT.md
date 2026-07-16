# 🗺️ Roadmap Sistem AI Multi-Agent laris.AI

> Dokumen ini menjelaskan arsitektur lengkap, alur kerja, dan roadmap pengembangan sistem AI Multi-Agent laris.AI untuk owner UMKM Indonesia.

---

## 🎯 Visi

> "Setiap UMKM Indonesia punya asisten AI pribadi yang bantu catat transaksi, balas customer, dan kasih saran bisnis — cukup lewat WhatsApp."

---

## 🏗️ ARSITEKTUR SISTEM (Big Picture)

```
┌─────────────────────────────────────────────────────────────────┐
│                       END USERS                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Customer   │  │    Owner     │  │    Admin     │         │
│  │   (WA CS)    │  │   (WA Catat) │  │  (Streamlit) │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          │ Chat             │ Chat             │ Login
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FONNTE (WhatsApp Gateway)                    │
│         Forward pesan masuk ke webhook kita                    │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│          KITA-CUAN-WA-BOT (Railway: Orchestrator)              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Receive webhook dari Fonnte                          │   │
│  │ 2. Detect: Owner or Customer?                          │   │
│  │ 3. Resolve: Tenant mana? (by owner_phones / device)    │   │
│  │ 4. Route ke agent yang sesuai                           │   │
│  │ 5. Kirim balasan via Fonnte                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└────┬───────────────────────────────────┬────────────────────────┘
     │                                   │
     │ Owner route                       │ Customer route
     ▼                                   ▼
┌─────────────────────────┐    ┌──────────────────────────────┐
│  AI CATAT AGENT         │    │  AI CS / SALES AGENT          │
│  (bukuwarung-ai)        │    │  (bukuwarung-ai)              │
│                         │    │                               │
│ - Vision extractor      │    │ - Multi-agent orchestrator    │
│   (foto struk)          │    │   • intent classifier         │
│ - Text parser           │    │   • product recommendation    │
│ - Transaction writer    │    │   • sales closer              │
│ - Approval generator    │    │   • support agent             │
└────────┬────────────────┘    └────────┬─────────────────────┘
         │                             │
         │         ┌───────────────────┘
         │         │
         ▼         ▼
┌──────────────────────────────────────────┐
│         SUPABASE (PostgreSQL)            │
│  ┌────────────────────────────────────┐  │
│  │ auth.users        (login)          │  │
│  │ clients           (multi-tenant)   │  │
│  │ warehouses        (per toko)       │  │
│  │ products          (per toko)       │  │
│  │ transactions      (per toko)       │  │
│  │ wa_messages       (chat log)       │  │
│  │ wa_users          (owner mapping)  │  │
│  │ approvals         (AI actions)     │  │
│  │ otak_memories     (AI learning)    │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
         ▲
         │
┌────────┴────────┐
│   STREAMLIT     │
│   (Dashboard)   │
│                │
│ - Login        │
│ - 9 menu       │
│ - Approval     │
│ - Gudang view  │
│ - Laporan KUR  │
│ - Free tier    │
└────────────────┘
```

---

## 🤖 AGENT BREAKDOWN

### Agent 1: **AI CATAT** (Owner-Side)

**Tugas**: Bantu owner catat transaksi via WhatsApp.

**Input**:
- Text biasa: `"beli indomie 5000"`, `"jual kopi 3500"`, `"bayar listrik 200000"`
- Foto struk / nota → Vision extractor (LLM baca gambar)
- Voice note → (planned) Speech-to-text

**Flow**:
```
Owner chat "beli indomie 5000"
  ↓
Bot detect OWNER (resolve_user_id)
  ↓
Classify intent → CATAT
  ↓
Parse: type=Pengeluaran, name=indomie, amount=5000
  ↓
Cek stok (kalau barang)
  ↓
Insert ke transactions + decrement products.stock
  ↓
Kirim approval request ke Ruang Komando
  ↓
Owner approve/tolak di Streamlit
```

**Output**:
- ✅ Transaksi tersimpan di database
- ✅ Approval muncul di Ruang Komando
- ✅ Update saldo otomatis

---

### Agent 2: **AI CS / Sales** (Customer-Side)

**Tugas**: Balas customer yang chat ke nomor toko.

**Sub-agents dalam Multi-Agent Orchestrator**:
- **Intent Classifier** → detect: greeting / tanya_produk / order / komplain / dll
- **Product Recommender** → cari produk yang sesuai
- **Sales Closer** → handle order / closing
- **Support Agent** → handle komplain / FAQ

**Flow**:
```
Customer chat "berapa harga indomie?"
  ↓
Bot detect CUSTOMER (resolve_user_id → ValueError → None)
  ↓
Resolve tenant by device (6285789974981 → Toko Rafih)
  ↓
Forward ke CS Agent webhook
  ↓
Orchestrator:
  ├─ Intent: "product_inquiry"
  ├─ Query products WHERE name ILIKE '%indomie%'
  ├─ Format: "Indomie Rp 3.500, stok: 20. Mau beli?"
  ↓
CS Agent kirim WA langsung via Fonnte
  ↓
Bot TIDAK kirim ulang (anti double-send)
  ↓
Customer dapat 1 pesan dari CS
```

**Output**:
- ✅ Customer dibalas dalam 5-10 detik
- ✅ Log tersimpan di `wa_messages`
- ✅ Owner bisa lihat di dashboard Streamlit

---

### Agent 3: **AI Memory (Otak)**

**Tugas**: Bikin AI "semakin pintar" seiring waktu.

**Mekanisme**:
1. Setiap Q&A customer → simpan ke tabel `otak_memories`
2. Chat berikutnya dengan pertanyaan mirip → ambil dari memory (no LLM call)
3. Hemat cost + response lebih cepat

**Contoh**:
```
# Chat pertama (butuh LLM)
Customer: "Apakah buka hari Minggu?"
Bot: "Buka dari jam 8 pagi sampai 9 malam, setiap hari termasuk Minggu."
[save to otak_memories]

# Chat ke-50 (dari memory, hemat LLM)
Customer: "Minggu buka ga?"
Bot: "Buka dari jam 8 pagi sampai 9 malam, setiap hari termasuk Minggu."  ← dari memory
```

---

## 📊 ALUR KERJA END-TO-END

### Skenario A: Owner Catat Transaksi

```
1. Owner chat ke nomor Owner: "beli indomie 5000"
2. Fonnte → webhook kita
3. Bot resolve_user_id(phone_owner) → UUID owner
4. Classify intent: CATAT
5. Parse transaksi: type=Pengeluaran, items=[{name:indomie, amount:5000}]
6. Insert ke transactions table (status=PENDING)
7. Insert ke approvals (untuk owner approve di dashboard)
8. Bot reply: "Siap Bos! Transaksi dicatat. Cek di Ruang Komando ya 🙏"
9. Owner buka Streamlit → Ruang Komando → Approve
10. Transaksi jadi status=APPROVED, muncul di Buku Kas
```

### Skenario B: Customer Tanya Produk

```
1. Customer chat ke nomor CS: "berapa harga indomie?"
2. Fonnte → webhook kita
3. Bot resolve_user_id(customer_phone) → ValueError → treated as CUSTOMER
4. Resolve tenant by device → Toko Rafih (UUID 1eaa96...)
5. Cek otak_memories: ada jawaban serupa? → kalau ya, return cached
6. Forward ke CS Agent webhook dengan payload:
   {
     "message": "berapa harga indomie?",
     "sender": "6281234567890",
     "user_id": "1eaa96...",
     "name": "Budi"
   }
7. CS Agent orchestrate:
   - Intent: product_inquiry
   - Query: SELECT * FROM products WHERE name ILIKE '%indomie%'
   - Format response
8. CS Agent kirim WA langsung via Fonnte
9. Return {status: "ok"} ke bot
10. Bot TIDAK kirim WA lagi (anti double-send)
11. Log tersimpan di wa_messages
```

### Skenario C: Admin Monitoring

```
1. Admin login ke laris-ai.streamlit.app dengan rafihrr1@gmail.com
2. Buka menu Ruang Komando → lihat:
   - Pending approvals
   - Banner Free Tier (kalau free) atau badge Pro
   - Aktivitas WhatsApp terbaru
3. Buka menu Gudang → lihat semua toko & produk
4. Buka menu Pengaturan Bot → lihat config bot per toko
5. Approve/reject transaksi → AI eksekusi
```

---

## 🛣️ ROADMAP PENGEMBANGAN

### ✅ Phase 1: MVP (Sudah Selesai)

| Fitur | Status |
|-------|--------|
| Streamlit dashboard (9 menu) | ✅ |
| Multi-tenant routing | ✅ |
| AI Catat (owner) | ✅ |
| AI CS (customer) | ✅ |
| Fonnte integration | ✅ |
| Supabase multi-tenant | ✅ |
| Approval workflow | ✅ |
| Vision extractor (foto struk) | ✅ |
| Free Tier banner | ✅ |
| AI Memory (otak) | ✅ |

### 🚧 Phase 2: Stabilization (Sedang Berjalan)

| Fitur | Status |
|-------|--------|
| Fix routing customer → CS Agent | ✅ Deployed |
| Fix `client_id` vs `user_id` mapping | 🚧 Worker berjalan |
| Anti double-send CS Agent | ✅ Deployed |
| Free tier SQL migration | ✅ Schema OK |
| Banner Free/Pro UI | ✅ |

### 📅 Phase 3: Monetization (1-2 Bulan)

| Fitur | Target |
|-------|--------|
| Plan tier enforcement (rate limit) | 🔜 Q1 |
| Payment gateway (Midtrans/Xendit) | 🔜 Q1 |
| Auto-downgrade expired plans | 🔜 Q1 |
| Invoice generation | 🔜 Q1 |
| Email reminder plan expired | 🔜 Q2 |
| WhatsApp broadcast marketing | 🔜 Q2 |

### 📅 Phase 4: Scale (3-6 Bulan)

| Fitur | Target |
|-------|--------|
| Voice note support (speech-to-text) | 🔜 Q2 |
| Multi-language (Jawa, Sunda) | 🔜 Q2 |
| Dashboard analytics | 🔜 Q3 |
| Mobile app (React Native) | 🔜 Q3 |
| Marketplace integrasi (Shopee, Tokopedia) | 🔜 Q4 |
| Bank reconciliation | 🔜 Q4 |

### 📅 Phase 5: Enterprise (6-12 Bulan)

| Fitur | Target |
|-------|--------|
| Custom AI model (fine-tuned per UMKM) | 🔜 2027 |
| Predictive analytics (forecast omzet) | 🔜 2027 |
| Multi-cabang (1 owner, banyak toko) | 🔜 2027 |
| White-label untuk reseller | 🔜 2027 |

---

## 📊 METRIK SUKSES (KPIs)

| Metrik | Target Q1 | Target Q2 |
|--------|-----------|-----------|
| Active tenants | 10 | 50 |
| Transactions/bulan | 1.000 | 10.000 |
| Customer chat response time | < 10 detik | < 5 detik |
| CS Agent accuracy | > 80% | > 90% |
| Customer satisfaction | 4.5/5 | 4.7/5 |
| Monthly recurring revenue (MRR) | Rp 5 jt | Rp 25 jt |

---

## 🔒 SECURITY & COMPLIANCE

| Aspek | Implementasi |
|-------|--------------|
| Multi-tenant isolation | 3 layer (app, session, RLS) |
| API key security | Env vars (Railway + Streamlit secrets) |
| WA token isolation | Per-tenant di tabel `clients` |
| Row Level Security | Supabase RLS policies |
| Data backup | Supabase auto-backup daily |
| GDPR/UU PDP ready | User bisa request delete data |

---

## 🛠️ TECH STACK

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit + Custom CSS (Dasher theme) |
| Backend (Bot) | Python + FastAPI + httpx |
| Backend (Multi-Agent) | Python + FastAPI + CrewAI |
| AI/LLM | Groq (Llama-3.1-8b-instant) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth (Google OAuth) |
| WA Gateway | Fonnte |
| Hosting | Railway (bot + agents), Streamlit Cloud (dashboard) |
| Domain | Cloudflare |
| CI/CD | GitHub → Auto-deploy |

---

## 📞 Tim & Roles

| Role | Person |
|------|--------|
| Founder / Super Admin | Rafih (rafihrr1@gmail.com) |
| Developer | (multi-agent AI assisted) |
| Customer Success | (planned Q2) |

---

## 📚 Related Docs

- [Tutorial Daftar Client Baru](./TUTORIAL_DAFTAR_CLIENT.md)
- [Deploy Multi-Tenant Bot](./DEPLOY_MULTI_TENANT_BOT.md)
- [Fix Drag Drop](./FIX_DRAG_DROP.md)
- [Streamlit Service Fix](./FIX_STREAMLIT_SERVICE.md)
- [WA Users Insert Fix](./FIX_WA_USERS_INSERT.md)