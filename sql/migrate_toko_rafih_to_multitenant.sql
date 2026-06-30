-- =====================================================================
-- Migrasi toko_rafih (tabel clients) → Multi-Tenant (client_settings)
-- Project: tagyexrsuvogrlhcthcp
-- Jalankan di Supabase SQL Editor SETELAH supabase_schema.sql
-- =====================================================================
-- Prasyarat:
--   1. Tabel client_settings sudah ada (supabase_schema.sql)
--   2. Akun Auth sudah ada, contoh: rafiharliansyah34@gmail.com
--   3. Baris clients.client_id = 'toko_rafih' sudah terisi (sudah ada)
-- =====================================================================

-- Ganti email di bawah ini jika akun dashboard berbeda:
-- rafiharliansyah34@gmail.com

-- ---------------------------------------------------------------------------
-- 1) client_settings dari clients + auth.users
--    Starter 1 nomor: wa_cs = wa_catat, token CS = token Catat
-- ---------------------------------------------------------------------------
INSERT INTO public.client_settings (
  user_id,
  business_name,
  wa_cs,
  wa_catat,
  fonnte_token_cs,
  fonnte_token_catat,
  authorized_owners,
  is_active
)
SELECT
  u.id,
  c.name,
  COALESCE(c.owner_phones[1], '6285789974981'),
  COALESCE(c.owner_phones[1], '6285789974981'),
  COALESCE(c.fonnte_token, ''),
  COALESCE(c.fonnte_token, ''),
  to_jsonb(c.owner_phones),
  c.is_active
FROM public.clients c
CROSS JOIN auth.users u
WHERE c.client_id = 'toko_rafih'
  AND lower(u.email) = lower('rafiharliansyah34@gmail.com')
ON CONFLICT (user_id) DO UPDATE SET
  business_name = EXCLUDED.business_name,
  wa_cs = EXCLUDED.wa_cs,
  wa_catat = EXCLUDED.wa_catat,
  fonnte_token_cs = EXCLUDED.fonnte_token_cs,
  fonnte_token_catat = EXCLUDED.fonnte_token_catat,
  authorized_owners = EXCLUDED.authorized_owners,
  is_active = EXCLUDED.is_active,
  updated_at = now();

-- ---------------------------------------------------------------------------
-- 2) wa_users — hubungkan nomor owner ke user_id dashboard
-- ---------------------------------------------------------------------------
INSERT INTO public.wa_users (phone, user_id, label)
SELECT
  COALESCE(c.owner_phones[1], '6285789974981'),
  u.id::text,
  c.name
FROM public.clients c
CROSS JOIN auth.users u
WHERE c.client_id = 'toko_rafih'
  AND lower(u.email) = lower('rafiharliansyah34@gmail.com')
ON CONFLICT (phone) DO UPDATE
  SET user_id = EXCLUDED.user_id,
      label = EXCLUDED.label;

-- ---------------------------------------------------------------------------
-- 3) products — salin katalog JSON clients → tabel products (per user_id)
-- ---------------------------------------------------------------------------
INSERT INTO products (user_id, name, price, stock)
SELECT u.id, p->>'name', COALESCE((p->>'price')::int, 0), COALESCE((p->>'stock')::int, 0)
FROM public.clients c
CROSS JOIN auth.users u
CROSS JOIN LATERAL jsonb_array_elements(c.products) AS p
WHERE c.client_id = 'toko_rafih'
  AND lower(u.email) = lower('rafiharliansyah34@gmail.com')
  AND trim(COALESCE(p->>'name', '')) <> ''
  AND NOT EXISTS (
    SELECT 1 FROM products px
    WHERE px.user_id = u.id
      AND lower(px.name) = lower(p->>'name')
  );

-- ---------------------------------------------------------------------------
-- 4) Perbarui metadata clients (legacy) + webhook path baru
-- ---------------------------------------------------------------------------
UPDATE public.clients c
SET metadata = COALESCE(c.metadata, '{}'::jsonb) || jsonb_build_object(
  'user_id', u.id::text,
  'wa_cs', COALESCE(c.owner_phones[1], '6285789974981'),
  'wa_catat', COALESCE(c.owner_phones[1], '6285789974981'),
  'whatsapp_cs_display', '085789974981',
  'whatsapp_catat_display', '085789974981',
  'webhook_cs', 'https://bukuwarung-ai-larisai.up.railway.app/webhook/csat/' || u.id::text,
  'webhook_catat', 'https://bukuwarung-ai-larisai.up.railway.app/webhook/catat/' || u.id::text,
  'pattern', 'multitenant_v1',
  'migrated_at', now()::text
),
updated_at = now()
FROM auth.users u
WHERE c.client_id = 'toko_rafih'
  AND lower(u.email) = lower('rafiharliansyah34@gmail.com');

-- ---------------------------------------------------------------------------
-- 5) Verifikasi
-- ---------------------------------------------------------------------------
SELECT cs.user_id, cs.business_name, cs.wa_cs, cs.is_active,
       left(cs.fonnte_token_cs, 6) || '...' AS token_cs_preview,
       cs.authorized_owners
FROM public.client_settings cs
JOIN auth.users u ON u.id = cs.user_id
WHERE lower(u.email) = lower('rafiharliansyah34@gmail.com');

SELECT phone, user_id, label FROM public.wa_users WHERE phone = '6285789974981';

SELECT user_id, name, stock, price FROM public.products
WHERE user_id = (
  SELECT id FROM auth.users
  WHERE lower(email) = lower('rafiharliansyah34@gmail.com')
  LIMIT 1
);

SELECT client_id, metadata->>'webhook_cs' AS webhook_cs, metadata->>'user_id' AS linked_user
FROM public.clients WHERE client_id = 'toko_rafih';
