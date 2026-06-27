-- =====================================================================
-- Seed produk trial untuk Logistik AI (stok indomie, gula, dll.)
-- Jalankan di Supabase → SQL Editor SETELAH akun client trial dibuat.
--
-- LANGKAH:
-- 1) Ganti email di baris WHERE (satu tempat saja)
-- 2) Run seluruh script ini
-- =====================================================================

-- (Opsional) Lihat daftar akun jika lupa email:
-- SELECT id, email, created_at FROM auth.users ORDER BY created_at DESC LIMIT 20;

WITH trial AS (
  SELECT id AS user_id
  FROM auth.users
  WHERE email = 'rafiharliansyah34@gmail.com'
  LIMIT 1
)
INSERT INTO products (user_id, name, price, stock)
SELECT t.user_id, p.name, p.price, p.stock
FROM trial t
CROSS JOIN (
  VALUES
    ('indomie', 3500, 20),
    ('gula', 15000, 10),
    ('minyak', 18000, 8),
    ('kopi', 3500, 50)
) AS p(name, price, stock)
WHERE t.user_id IS NOT NULL;

-- Update kopi jika sudah pernah di-seed (harga 3500, stok 50)
UPDATE products p
SET price = 3500, stock = 50
FROM auth.users u
WHERE p.user_id::text = u.id::text
  AND lower(u.email) = lower('rafiharliansyah34@gmail.com')
  AND lower(p.name) = 'kopi';

-- Jika 0 baris ter-insert → email salah atau akun belum dibuat.
-- Verifikasi:
-- SELECT p.* FROM products p
-- JOIN auth.users u ON u.id::text = p.user_id::text
-- WHERE u.email = 'GANTI_EMAIL_CLIENT@disini.com';

-- Opsional di Railway bot: STOCK_THRESHOLD=5, REORDER_QTY=20
