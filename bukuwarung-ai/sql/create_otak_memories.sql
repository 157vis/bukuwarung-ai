-- Tabel memory Otak AI (jalankan di Supabase SQL Editor)
create table if not exists otak_memories (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  content text not null,
  embedding jsonb not null default '[]',
  timestamp timestamptz not null default now(),
  feedback_score float not null default 0,
  weight float not null default 1.0,
  status text not null default 'active',
  metadata jsonb default '{}'
);

create index if not exists idx_otak_memories_user on otak_memories(user_id);
create index if not exists idx_otak_memories_status on otak_memories(status);

alter table otak_memories enable row level security;
