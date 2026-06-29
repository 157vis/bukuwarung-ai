-- Registry client / tenant (multi-UMKM dalam satu deploy Railway)
create table if not exists clients (
  client_id text primary key,
  name text not null,
  fonnte_token text not null default '',
  owner_phones text[] not null default '{}',
  profile_key text not null default 'ramah_warm',
  products jsonb not null default '[]',
  payment_methods jsonb not null default '[]',
  is_active boolean not null default true,
  metadata jsonb not null default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_clients_fonnte_token on clients (fonnte_token) where fonnte_token <> '';

-- Contoh onboarding client baru:
-- insert into clients (client_id, name, fonnte_token, owner_phones, profile_key, products, payment_methods)
-- values (
--   'toko_berkah',
--   'Warung Berkah',
--   'FONNTE_TOKEN_DEVICE_1',
--   array['6281234567890'],
--   'ramah_warm',
--   '[{"name":"kopi","price":3500,"stock":50}]'::jsonb,
--   '[{"bank":"BCA","account_number":"1234567890","account_name":"Warung Berkah","type":"transfer"}]'::jsonb
-- );

alter table clients enable row level security;
