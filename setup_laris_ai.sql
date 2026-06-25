-- =====================================================================
-- Laris.AI - Setup lengkap (idempotent, aman dijalankan berulang).
-- Jalankan SEKALI di Supabase -> SQL Editor untuk project Anda.
-- Lalu jalankan baris paling bawah: NOTIFY pgrst, 'reload schema';
-- =====================================================================

-- 1) APPROVALS: jantung "Ruang Komando" (Proactive UI)
create table if not exists approvals (
  id          bigserial primary key,
  user_id     text        not null,
  agent_id    text        not null,            -- 'admin' | 'logistik' | ...
  action_type text        not null,            -- 'create_po' | 'promo' | 'broadcast' | ...
  summary     text        not null,            -- ringkasan dari AI (Bahasa Indonesia)
  payload     jsonb,                            -- detail aksi (produk, qty, supplier, dst)
  status      text        not null default 'PENDING', -- PENDING | APPROVED | REJECTED
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);
create index if not exists idx_approvals_user_status on approvals(user_id, status);

-- 2) WA_MESSAGES: log percakapan untuk widget Chat History
create table if not exists wa_messages (
  id         bigserial primary key,
  user_id    text        not null,
  phone      text,
  role       text        not null,             -- 'user' | 'assistant'
  agent_id   text,                              -- 'admin' | 'logistik' (jika assistant)
  content    text        not null,
  created_at timestamptz default now()
);
create index if not exists idx_wa_messages_user on wa_messages(user_id, created_at);

-- 3) WA_USERS: PEMETAAN nomor WhatsApp -> client (user_id).
--    Inilah yang membuat "tambah client baru" jadi mudah & multi-tenant.
create table if not exists wa_users (
  id         bigserial primary key,
  phone      text unique not null,             -- nomor WA ternormalisasi (mis. 6281234567890)
  user_id    text        not null,             -- id user Supabase Auth (pemilik usaha)
  label      text,                              -- opsional: nama toko / catatan
  created_at timestamptz default now()
);
create index if not exists idx_wa_users_user on wa_users(user_id);

-- 4) Paksa PostgREST memuat ulang schema cache (hilangkan error PGRST205).
NOTIFY pgrst, 'reload schema';
