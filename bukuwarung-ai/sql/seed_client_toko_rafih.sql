-- =====================================================================
-- Seed client: Toko Rafih | WA 085789974981 → 6285789974981
-- Jalankan di Supabase SQL Editor (project tagyexrsuvogrlhcthcp)
-- =====================================================================

-- 0) Pastikan tabel ada
-- (jalankan dulu jika belum: bukuwarung-ai/sql/create_clients.sql)
-- (jalankan dulu jika belum: bukuwarung-ai/sql/create_brand_voices.sql)

-- 1) Client registry BukuWarung-AI
INSERT INTO clients (
  client_id,
  name,
  fonnte_token,
  owner_phones,
  profile_key,
  products,
  payment_methods,
  is_active,
  metadata
) VALUES (
  'toko_rafih',
  'Toko Rafih',
  '',  -- isi token Fonnte device setelah punya: UPDATE clients SET fonnte_token='...' WHERE client_id='toko_rafih';
  array['6285789974981'],
  'ramah_warm',
  '[
    {"name": "kopi", "price": 3500, "stock": 50},
    {"name": "indomie", "price": 3500, "stock": 20},
    {"name": "gula", "price": 15000, "stock": 10},
    {"name": "minyak", "price": 18000, "stock": 8}
  ]'::jsonb,
  '[
    {"bank": "BCA", "account_number": "1234567890", "account_name": "Toko Rafih", "type": "transfer"},
    {"provider": "GoPay", "account_number": "085789974981", "account_name": "Toko Rafih", "type": "ewallet"},
    {"provider": "QRIS", "account_number": "QRIS-TOKO-RAFIH", "type": "qris"}
  ]'::jsonb,
  true,
  '{"whatsapp_display": "085789974981", "webhook_path": "/webhook-whatsapp/toko_rafih"}'::jsonb
)
ON CONFLICT (client_id) DO UPDATE SET
  name = EXCLUDED.name,
  owner_phones = EXCLUDED.owner_phones,
  profile_key = EXCLUDED.profile_key,
  products = EXCLUDED.products,
  payment_methods = EXCLUDED.payment_methods,
  is_active = EXCLUDED.is_active,
  metadata = EXCLUDED.metadata,
  updated_at = now();

-- 2) Brand voice (personality engine)
INSERT INTO brand_voices (
  client_id,
  profile_key,
  greeting_style,
  emoji_usage,
  formality_level,
  language_mix
) VALUES (
  'toko_rafih',
  'ramah_warm',
  'hangat',
  2,
  1,
  'id'
)
ON CONFLICT (client_id) DO UPDATE SET
  profile_key = EXCLUDED.profile_key,
  greeting_style = EXCLUDED.greeting_style,
  emoji_usage = EXCLUDED.emoji_usage,
  formality_level = EXCLUDED.formality_level,
  language_mix = EXCLUDED.language_mix,
  updated_at = now();

-- 3) (Opsional) Hubungkan WA ke akun laris.AI jika user Auth sudah ada
INSERT INTO wa_users (phone, user_id, label)
SELECT '6285789974981', u.id::text, 'Toko Rafih'
FROM auth.users u
WHERE lower(u.email) = lower('rafiharliansyah34@gmail.com')
LIMIT 1
ON CONFLICT (phone) DO UPDATE
  SET user_id = EXCLUDED.user_id,
      label = EXCLUDED.label;

-- 4) Verifikasi
SELECT client_id, name, owner_phones, profile_key, is_active
FROM clients
WHERE client_id = 'toko_rafih';

SELECT client_id, profile_key FROM brand_voices WHERE client_id = 'toko_rafih';

SELECT phone, user_id, label FROM wa_users WHERE phone = '6285789974981';
