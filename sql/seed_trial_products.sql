-- =====================================================================
-- Seed produk trial untuk client UMKM (Logistik AI / stok).
-- GANTI 'USER_ID_TRIAL' dengan user_id Supabase Auth client trial Anda.
-- Jalankan di Supabase SQL Editor SETELAH akun trial dibuat.
-- =====================================================================

-- Contoh: ganti dengan UUID user trial (dari menu Pengaturan admin setelah buat client)
-- SELECT id, email FROM auth.users WHERE email = 'trial@contoh.com';

insert into products (user_id, name, stock) values
  ('USER_ID_TRIAL', 'indomie', 20),
  ('USER_ID_TRIAL', 'gula', 10),
  ('USER_ID_TRIAL', 'minyak', 8),
  ('USER_ID_TRIAL', 'kopi', 15);

-- Opsional: set ambang stok di bot (.env): STOCK_THRESHOLD=5, REORDER_QTY=20
