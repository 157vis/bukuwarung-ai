-- Brand voice per client (personality engine)
create table if not exists brand_voices (
  client_id text primary key,
  profile_key text not null default 'ramah_warm',
  greeting_style text default 'hangat',
  emoji_usage int not null default 2,
  formality_level int not null default 1,
  language_mix text default 'id',
  custom_overrides jsonb default '{}',
  updated_at timestamptz default now()
);

alter table brand_voices enable row level security;
