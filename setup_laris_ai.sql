-- =====================================================================
-- Laris.AI - Setup database LENGKAP + Row Level Security (RLS).
-- Idempotent: aman dijalankan berulang.
-- Jalankan SEKALI di Supabase -> SQL Editor untuk project Anda.
--
-- Arsitektur keamanan:
--   * Aplikasi Streamlit pakai ANON key + meneruskan JWT user login,
--     sehingga auth.uid() dikenali dan RLS membatasi data per-user.
--   * Bot WhatsApp (kita-cuan-wa-bot) WAJIB pakai SERVICE_ROLE key,
--     yang otomatis BYPASS RLS (bot bertindak atas nama banyak user).
--   * Super Admin (email di bawah) boleh kelola semua pemetaan wa_users.
-- =====================================================================

-- Ganti bila email Super Admin berubah:
--   (dipakai di policy admin wa_users di bagian RLS bawah)
--   Super Admin: rafihrr1@gmail.com

-- =====================================================================
-- 1) TABEL
-- =====================================================================

-- 1a) TRANSACTIONS: buku kas (pemasukan/pengeluaran)
create table if not exists transactions (
  id              bigserial primary key,
  user_id         text        not null,
  date            text,                            -- 'YYYY-MM-DD HH:MM' (disimpan sebagai teks oleh app)
  type            text        not null,            -- 'Pemasukan' | 'Pengeluaran'
  category        text,
  amount          numeric     not null default 0,
  note            text,
  receipt_no      text,
  running_balance numeric     default 0,
  is_prive        boolean     default false,
  created_at      timestamptz default now()
);
create index if not exists idx_transactions_user on transactions(user_id, id desc);

-- 1b) PRODUCTS: stok produk (dipakai Logistik AI / bot)
create table if not exists products (
  id         bigserial primary key,
  user_id    text        not null,
  name       text        not null,
  stock      integer     default 0,
  created_at timestamptz default now()
);
create index if not exists idx_products_user on products(user_id);

-- 1c) WAREHOUSES: gudang
create table if not exists warehouses (
  id         bigserial primary key,
  user_id    text        not null,
  name       text        not null,
  location   text,
  notes      text,
  created_at timestamptz default now()
);
create index if not exists idx_warehouses_user on warehouses(user_id);

-- 1d) INVENTORY_ENTRIES: kartu stok (masuk/keluar) per gudang
create table if not exists inventory_entries (
  id           bigserial primary key,
  user_id      text        not null,
  warehouse_id bigint      references warehouses(id) on delete cascade,
  barang       text        not null,
  qty_in       integer     default 0,
  qty_out      integer     default 0,
  note         text,
  date         text,
  created_at   timestamptz default now()
);
create index if not exists idx_inventory_user on inventory_entries(user_id, id desc);

-- 1e) APPROVALS: jantung "Ruang Komando" (Proactive UI)
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

-- 1f) WA_MESSAGES: log percakapan untuk widget Chat History
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

-- 1g) WA_USERS: PEMETAAN nomor WhatsApp -> client (user_id). Multi-tenant.
create table if not exists wa_users (
  id         bigserial primary key,
  phone      text unique not null,             -- nomor WA ternormalisasi (mis. 6281234567890)
  user_id    text        not null,             -- id user Supabase Auth (pemilik usaha)
  label      text,                              -- opsional: nama toko / catatan
  created_at timestamptz default now()
);
create index if not exists idx_wa_users_user on wa_users(user_id);

-- =====================================================================
-- 2) ROW LEVEL SECURITY (RLS)
--    Pola: tiap user hanya boleh mengakses baris miliknya (user_id = auth.uid()).
--    service_role (bot) otomatis bypass. anon (belum login) tidak dapat apa-apa.
-- =====================================================================

-- 2a) transactions
alter table transactions enable row level security;
drop policy if exists p_own_transactions on transactions;
create policy p_own_transactions on transactions
  for all to authenticated
  using (user_id = (auth.uid())::text)
  with check (user_id = (auth.uid())::text);

-- 2b) products
alter table products enable row level security;
drop policy if exists p_own_products on products;
create policy p_own_products on products
  for all to authenticated
  using (user_id = (auth.uid())::text)
  with check (user_id = (auth.uid())::text);

-- 2c) warehouses
alter table warehouses enable row level security;
drop policy if exists p_own_warehouses on warehouses;
create policy p_own_warehouses on warehouses
  for all to authenticated
  using (user_id = (auth.uid())::text)
  with check (user_id = (auth.uid())::text);

-- 2d) inventory_entries
alter table inventory_entries enable row level security;
drop policy if exists p_own_inventory on inventory_entries;
create policy p_own_inventory on inventory_entries
  for all to authenticated
  using (user_id = (auth.uid())::text)
  with check (user_id = (auth.uid())::text);

-- 2e) approvals
alter table approvals enable row level security;
drop policy if exists p_own_approvals on approvals;
create policy p_own_approvals on approvals
  for all to authenticated
  using (user_id = (auth.uid())::text)
  with check (user_id = (auth.uid())::text);

-- 2f) wa_messages
alter table wa_messages enable row level security;
drop policy if exists p_own_wa_messages on wa_messages;
create policy p_own_wa_messages on wa_messages
  for all to authenticated
  using (user_id = (auth.uid())::text)
  with check (user_id = (auth.uid())::text);

-- 2g) wa_users: user lihat miliknya, Super Admin kelola semua.
alter table wa_users enable row level security;

drop policy if exists p_own_wa_users on wa_users;
create policy p_own_wa_users on wa_users
  for all to authenticated
  using (user_id = (auth.uid())::text)
  with check (user_id = (auth.uid())::text);

drop policy if exists p_admin_wa_users on wa_users;
create policy p_admin_wa_users on wa_users
  for all to authenticated
  using ((auth.jwt() ->> 'email') = 'rafihrr1@gmail.com')
  with check ((auth.jwt() ->> 'email') = 'rafihrr1@gmail.com');

-- =====================================================================
-- 3) Paksa PostgREST memuat ulang schema cache (hilangkan error PGRST205).
-- =====================================================================
NOTIFY pgrst, 'reload schema';
