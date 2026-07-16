-- ============================================================
-- laris.AI — Free Tier Plan (kolom minimal, real schema)
-- Tabel target: clients (sudah ada: client_id, name, fonnte_token,
--                              owner_phones, profile_key, products,
--                              payment_methods, is_active, metadata,
--                              created_at, updated_at)
-- ============================================================
-- CATATAN PENTING:
-- - Tabel `clients` TIDAK punya kolom `user_id` (pakai `client_id`)
-- - Semua perubahan pakai IF NOT EXISTS supaya aman dijalankan ulang
-- - Default semua user = 'free'
-- ============================================================

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS plan_tier TEXT NOT NULL DEFAULT 'free'
    CHECK (plan_tier IN ('free', 'pro', 'bisnis', 'kemitraan'));

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS plan_started_at TIMESTAMPTZ;

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ;

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS tx_count_this_month INTEGER NOT NULL DEFAULT 0;

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS tx_count_reset_at TIMESTAMPTZ;

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS customer_chat_count_this_month INTEGER NOT NULL DEFAULT 0;

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS customer_chat_reset_at TIMESTAMPTZ;

-- Index untuk query cepat
CREATE INDEX IF NOT EXISTS idx_clients_plan_tier
  ON clients(plan_tier);

CREATE INDEX IF NOT EXISTS idx_clients_plan_expires_at
  ON clients(plan_expires_at);

-- ============================================================
-- View: statistik tier (untuk dashboard monitoring)
-- ============================================================
CREATE OR REPLACE VIEW v_clients_tier_stats AS
SELECT
  plan_tier,
  COUNT(*) AS total_clients,
  COUNT(*) FILTER (WHERE is_active = true) AS active_clients,
  SUM(tx_count_this_month) AS total_tx_this_month,
  SUM(customer_chat_count_this_month) AS total_chats_this_month
FROM clients
GROUP BY plan_tier;

-- ============================================================
-- Function: auto-reset counter bulanan + auto-downgrade expired plan
-- Jalankan via cron / pg_cron (opsional, manual juga OK)
-- ============================================================
CREATE OR REPLACE FUNCTION reset_monthly_counters_if_due()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  affected_rows INTEGER;
BEGIN
  -- Reset transaction counter
  UPDATE clients
  SET tx_count_this_month = 0,
      tx_count_reset_at = NOW()
  WHERE tx_count_reset_at IS NULL
     OR tx_count_reset_at < date_trunc('month', NOW());
  GET DIAGNOSTICS affected_rows = ROW_COUNT;

  -- Reset customer chat counter
  UPDATE clients
  SET customer_chat_count_this_month = 0,
      customer_chat_reset_at = NOW()
  WHERE customer_chat_reset_at IS NULL
     OR customer_chat_reset_at < date_trunc('month', NOW());

  -- Auto-downgrade expired plans
  UPDATE clients
  SET plan_tier = 'free',
      plan_expires_at = NULL
  WHERE plan_tier != 'free'
    AND plan_tier != 'kemitraan'
    AND plan_expires_at IS NOT NULL
    AND plan_expires_at < NOW();

  RETURN affected_rows;
END;
$$;

-- ============================================================
-- Function: cek & increment transaction counter (untuk rate limit)
-- Returns: (allowed, current_count, limit)
-- ============================================================
CREATE OR REPLACE FUNCTION check_tx_quota(p_client_id TEXT)
RETURNS TABLE(allowed BOOLEAN, current_count INTEGER, max_allowed INTEGER)
LANGUAGE plpgsql
AS $$
DECLARE
  v_tier TEXT;
  v_count INTEGER;
  v_max INTEGER;
BEGIN
  -- Ambil tier
  SELECT plan_tier, tx_count_this_month
  INTO v_tier, v_count
  FROM clients
  WHERE client_id = p_client_id
  LIMIT 1;

  IF v_tier IS NULL THEN
    v_tier := 'free';
    v_count := 0;
  END IF;

  -- Tentukan limit per tier
  v_max := CASE v_tier
    WHEN 'free'      THEN 100   -- 100 transaksi / bulan
    WHEN 'pro'       THEN 1000
    WHEN 'bisnis'    THEN 10000
    WHEN 'kemitraan' THEN 999999
    ELSE 100
  END;

  RETURN QUERY SELECT (v_count < v_max), v_count, v_max;
END;
$$;

-- ============================================================
-- Function: increment transaction counter (dipanggil dari bot tiap catat transaksi)
-- Aman dipanggil walau function belum ada (fallback di Python)
-- ============================================================
CREATE OR REPLACE FUNCTION increment_tx_count(p_client_id TEXT)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_new_count INTEGER;
BEGIN
  UPDATE clients
  SET tx_count_this_month = COALESCE(tx_count_this_month, 0) + 1,
      tx_count_reset_at = COALESCE(tx_count_reset_at, NOW())
  WHERE client_id = p_client_id
  RETURNING tx_count_this_month INTO v_new_count;

  IF v_new_count IS NULL THEN
    v_new_count := 0;
  END IF;

  RETURN v_new_count;
END;
$$;

-- ============================================================
-- Function: increment customer chat counter (untuk CS Agent billing)
-- ============================================================
CREATE OR REPLACE FUNCTION increment_customer_chat_count(p_client_id TEXT)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_new_count INTEGER;
BEGIN
  UPDATE clients
  SET customer_chat_count_this_month = COALESCE(customer_chat_count_this_month, 0) + 1,
      customer_chat_reset_at = COALESCE(customer_chat_reset_at, NOW())
  WHERE client_id = p_client_id
  RETURNING customer_chat_count_this_month INTO v_new_count;

  IF v_new_count IS NULL THEN
    v_new_count := 0;
  END IF;

  RETURN v_new_count;
END;
$$;

-- ============================================================
-- Seed data awal: set Toko Rafih = pro (untuk testing)
-- UNCOMMENT kalau mau set Toko Rafih sebagai Pro
-- ============================================================
-- UPDATE clients
-- SET plan_tier = 'pro',
--     plan_started_at = NOW(),
--     plan_expires_at = NOW() + INTERVAL '30 days'
-- WHERE client_id = 'toko_rafih';

-- ============================================================
-- Verifikasi schema
-- ============================================================
SELECT
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_name = 'clients'
  AND column_name IN (
    'plan_tier', 'plan_started_at', 'plan_expires_at',
    'tx_count_this_month', 'tx_count_reset_at',
    'customer_chat_count_this_month', 'customer_chat_reset_at'
  )
ORDER BY column_name;