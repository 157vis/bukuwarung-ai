-- =====================================================================
-- Setup client: rafiharliansyah34@gmail.com | WA 082112826851
-- Jalankan SELURUH file ini di Supabase → SQL Editor (project tagyexrsuvogrlhcthcp)
-- =====================================================================

-- 0) Pastikan akun Auth sudah ada (harus ada 1 baris)
SELECT id AS user_id, email, created_at
FROM auth.users
WHERE lower(email) = lower('rafiharliansyah34@gmail.com');

-- Jika query di atas KOSONG → buat dulu client di dashboard admin:
--   Streamlit → Pengaturan → Tambah Client Baru
--   Email: rafiharliansyah34@gmail.com + password sementara
-- Lalu jalankan ulang script ini.

-- 1) Hubungkan nomor WhatsApp ke akun client
INSERT INTO wa_users (phone, user_id, label)
SELECT '6282112826851', u.id::text, 'Rafi Harliansyah'
FROM auth.users u
WHERE lower(u.email) = lower('rafiharliansyah34@gmail.com')
LIMIT 1
ON CONFLICT (phone) DO UPDATE
  SET user_id = EXCLUDED.user_id,
      label = EXCLUDED.label;

-- 2) Seed produk untuk Logistik AI (kolom price wajib di DB Anda)
INSERT INTO products (user_id, name, price, stock)
SELECT u.id, v.name, v.price, v.stock
FROM auth.users u
CROSS JOIN (
  VALUES
    ('indomie', 3500, 20),
    ('gula', 15000, 10),
    ('minyak', 18000, 8),
    ('kopi', 2500, 15)
) AS v(name, price, stock)
WHERE lower(u.email) = lower('rafiharliansyah34@gmail.com')
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.user_id::text = u.id::text
      AND lower(p.name) = lower(v.name)
  );

-- 3) Verifikasi — harus ada data di ketiga query ini
SELECT w.phone, w.user_id, w.label, u.email
FROM wa_users w
JOIN auth.users u ON u.id::text = w.user_id::text
WHERE w.phone = '6282112826851';

SELECT p.name, p.price, p.stock, u.email
FROM products p
JOIN auth.users u ON u.id::text = p.user_id::text
WHERE lower(u.email) = lower('rafiharliansyah34@gmail.com');

SELECT t.id, t.type, t.category, t.amount, t.note, t.date, u.email
FROM transactions t
JOIN auth.users u ON u.id::text = t.user_id::text
WHERE lower(u.email) = lower('rafiharliansyah34@gmail.com')
ORDER BY t.id DESC
LIMIT 10;

-- 4) (Opsional) Salin user_id ke Railway bot → Variable WA_DEFAULT_USER_ID
-- SELECT id FROM auth.users WHERE lower(email) = lower('rafiharliansyah34@gmail.com');
