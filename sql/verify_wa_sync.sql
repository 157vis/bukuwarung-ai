-- =====================================================================
-- Verifikasi sinkronisasi Bot WA ↔ Dashboard Streamlit
-- Jalankan di Supabase → SQL Editor (ganti email di baris WHERE)
-- =====================================================================

-- 1) Akun client + user_id
SELECT id AS user_id, email, created_at
FROM auth.users
WHERE email = 'rafiharliansyah34@gmail.com';

-- 2) Nomor WA terhubung ke user_id mana?
SELECT w.phone, w.user_id, w.label, u.email
FROM wa_users w
LEFT JOIN auth.users u ON u.id::text = w.user_id::text
ORDER BY w.created_at DESC;

-- 3) Transaksi dari bot (harus user_id sama dengan akun login Streamlit)
SELECT t.id, t.user_id, t.type, t.category, t.amount, t.note, t.date, u.email
FROM transactions t
LEFT JOIN auth.users u ON u.id::text = t.user_id::text
WHERE u.email = 'rafiharliansyah34@gmail.com'
ORDER BY t.id DESC
LIMIT 20;

-- 4) Log chat WA di Ruang Komando
SELECT m.role, m.content, m.created_at, u.email
FROM wa_messages m
LEFT JOIN auth.users u ON u.id::text = m.user_id::text
WHERE u.email = 'rafiharliansyah34@gmail.com'
ORDER BY m.created_at DESC
LIMIT 20;

-- Jika (2) kosong → jalankan sql/link_wa_number.sql
-- Jika (3) kosong tapi bot balas "Tercatat" → user_id di wa_users salah
-- Jika (3) ada data tapi dashboard kosong → login Streamlit pakai email yang SALAH
