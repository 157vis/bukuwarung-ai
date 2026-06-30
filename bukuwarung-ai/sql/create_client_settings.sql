-- Sama dengan supabase_schema.sql di root repo — jalankan di Supabase SQL Editor.



-- ---------------------------------------------------------------------------

-- client_settings: konfigurasi per tenant (token Fonnte, owner WA, bisnis)

-- ---------------------------------------------------------------------------

create table if not exists public.client_settings (

  user_id uuid primary key references auth.users (id) on delete cascade,

  business_name text not null default '',

  wa_cs text not null default '',

  wa_catat text not null default '',

  fonnte_token_cs text not null default '',

  fonnte_token_catat text not null default '',

  authorized_owners jsonb not null default '[]'::jsonb,

  is_active boolean not null default true,

  created_at timestamptz not null default now(),

  updated_at timestamptz not null default now()

);



comment on table public.client_settings is

  'Pengaturan bot WA per tenant. Token Fonnte & authorized owners hanya di sini.';



create index if not exists idx_client_settings_active

  on public.client_settings (is_active)

  where is_active = true;



alter table public.client_settings enable row level security;



drop policy if exists "client_settings_select_own" on public.client_settings;

drop policy if exists "client_settings_insert_own" on public.client_settings;

drop policy if exists "client_settings_update_own" on public.client_settings;

drop policy if exists "client_settings_delete_own" on public.client_settings;



create policy "client_settings_select_own"

  on public.client_settings for select to authenticated

  using (auth.uid() = user_id);



create policy "client_settings_insert_own"

  on public.client_settings for insert to authenticated

  with check (auth.uid() = user_id);



create policy "client_settings_update_own"

  on public.client_settings for update to authenticated

  using (auth.uid() = user_id) with check (auth.uid() = user_id);



create policy "client_settings_delete_own"

  on public.client_settings for delete to authenticated

  using (auth.uid() = user_id);



create or replace function public.set_client_settings_updated_at()

returns trigger language plpgsql as $$

begin

  new.updated_at = now();

  return new;

end;

$$;



drop trigger if exists trg_client_settings_updated_at on public.client_settings;

create trigger trg_client_settings_updated_at

  before update on public.client_settings

  for each row execute function public.set_client_settings_updated_at();



-- Muat ulang cache schema PostgREST (hindari "tabel belum ada" di dashboard)

notify pgrst, 'reload schema';


