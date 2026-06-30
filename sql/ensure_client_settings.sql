-- =====================================================================
-- client_settings sudah ada? Cukup jalankan baris NOTIFY di bawah.
-- Belum ada? Jalankan dulu: bukuwarung-ai/sql/create_client_settings.sql
-- Project: tagyexrsuvogrlhcthcp
-- =====================================================================

notify pgrst, 'reload schema';

-- Verifikasi cepat:
select count(*) as baris_client_settings from public.client_settings;
