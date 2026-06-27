-- =====================================================================
-- Daftarkan nomor WhatsApp ke akun client (tabel wa_users).
-- Jalankan di Supabase → SQL Editor.
--
-- LANGKAH:
-- 1) Ganti EMAIL client di baris WHERE
-- 2) (Opsional) ganti nomor WA jika beda
-- 3) Run seluruh script
-- =====================================================================

-- (Opsional) Lihat user_id:
-- SELECT id, email FROM auth.users ORDER BY created_at DESC LIMIT 20;

INSERT INTO wa_users (phone, user_id, label)
SELECT '6282112826851', u.id::text, 'Trial UMKM'
FROM auth.users u
WHERE u.email = 'rafiharliansyah34@gmail.com'  -- client trial
LIMIT 1
ON CONFLICT (phone) DO UPDATE
  SET user_id = EXCLUDED.user_id,
      label = EXCLUDED.label;

-- Verifikasi:
-- SELECT w.*, u.email FROM wa_users w
-- JOIN auth.users u ON u.id::text = w.user_id::text
-- WHERE w.phone = '6282112826851';
