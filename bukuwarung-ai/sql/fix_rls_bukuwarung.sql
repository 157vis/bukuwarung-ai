-- =====================================================================
-- Fix RLS untuk tabel BukuWarung-AI (jalankan di Supabase SQL Editor)
--
-- Gejala: bot balas "Maaf, ada gangguan sebentar..."
-- Error: new row violates row-level security policy for table "otak_memories"
--
-- Alternatif terbaik: pakai SUPABASE_KEY = service_role di Railway (bypass RLS).
-- File ini untuk jika Anda tetap memakai anon key.
-- =====================================================================

-- otak_memories
drop policy if exists bukuwarung_otak_all on otak_memories;
create policy bukuwarung_otak_all on otak_memories
  for all using (true) with check (true);

-- brand_voices
drop policy if exists bukuwarung_brand_all on brand_voices;
create policy bukuwarung_brand_all on brand_voices
  for all using (true) with check (true);

-- clients
drop policy if exists bukuwarung_clients_all on clients;
create policy bukuwarung_clients_all on clients
  for all using (true) with check (true);

-- Verifikasi
select tablename, policyname from pg_policies
where tablename in ('otak_memories', 'brand_voices', 'clients')
order by tablename, policyname;
