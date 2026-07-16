-- ============================================================
-- laris.AI — Tambah Kolom Info Toko untuk CS Agent
-- Tujuan: CS Agent punya data spesifik per toko untuk jawab pertanyaan
--         lokasi, jam buka, metode bayar, dll — bukan fallback hardcoded.
-- ============================================================
-- Tabel target: clients (PK = client_id, sudah ada di real schema)
-- Approach: Tambah kolom langsung ke tabel clients (bukan JSONB metadata)
--            agar query lebih cepat + type-safe
-- ============================================================

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS business_name TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS jam_buka      TEXT NOT NULL DEFAULT '07:00',
  ADD COLUMN IF NOT EXISTS jam_tutup     TEXT NOT NULL DEFAULT '21:00',
  ADD COLUMN IF NOT EXISTS hari_operasional TEXT NOT NULL DEFAULT 'Setiap hari',
  ADD COLUMN IF NOT EXISTS alamat        TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS kota          TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS no_telp       TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS ongkir_info   TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS metode_bayar  TEXT[] NOT NULL DEFAULT ARRAY['Cash','Transfer','QRIS'],
  ADD COLUMN IF NOT EXISTS tagline       TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Index untuk pencarian berdasarkan kota
CREATE INDEX IF NOT EXISTS idx_clients_kota ON clients(kota) WHERE kota <> '';
CREATE INDEX IF NOT EXISTS idx_clients_business_name ON clients(business_name) WHERE business_name <> '';

-- Backfill dari metadata JSONB (kalau sebelumnya sudah ada data di sana)
UPDATE clients
SET
  business_name = COALESCE(NULLIF(metadata->>'business_name', ''), business_name),
  alamat        = COALESCE(NULLIF(metadata->>'alamat', ''), alamat),
  no_telp       = COALESCE(NULLIF(metadata->>'no_telp', ''), no_telp)
WHERE
  metadata->>'business_name' IS NOT NULL
  OR metadata->>'alamat' IS NOT NULL
  OR metadata->>'no_telp' IS NOT NULL;

-- ============================================================
-- Seed Toko Rafih (kalau ada) dengan data contoh
-- ============================================================
UPDATE clients
SET
  business_name   = 'Toko Rafih',
  jam_buka        = '07:00',
  jam_tutup       = '21:00',
  hari_operasional= 'Senin - Minggu',
  alamat          = 'Jl. Pasar Baru No. 12',
  kota            = 'Jakarta',
  no_telp         = '0857-8997-4981',
  ongkir_info     = 'Belum ada layanan antar (ambil di tempat)',
  metode_bayar    = ARRAY['Cash','Transfer BCA','QRIS'],
  tagline         = 'Sembako murah lengkap, buka setiap hari!'
WHERE client_id = 'toko_rafih';

-- ============================================================
-- View: info lengkap toko (untuk dashboard)
-- ============================================================
CREATE OR REPLACE VIEW v_clients_full_info AS
SELECT
  client_id,
  name,
  business_name,
  COALESCE(NULLIF(business_name, ''), name) AS display_name,
  jam_buka,
  jam_tutup,
  hari_operasional,
  alamat,
  kota,
  no_telp,
  ongkir_info,
  metode_bayar,
  tagline,
  profile_key,
  owner_phones,
  fonnte_token,
  is_active,
  plan_tier,
  created_at,
  updated_at
FROM clients;

-- ============================================================
-- Function: ambil info toko untuk CS Agent
-- Returns: JSONB dengan semua data yang dibutuhkan CS
-- ============================================================
CREATE OR REPLACE FUNCTION get_client_info_for_cs(p_client_id TEXT)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v_result JSONB;
BEGIN
  SELECT jsonb_build_object(
    'client_id',         client_id,
    'name',              name,
    'business_name',     COALESCE(NULLIF(business_name, ''), name),
    'jam_buka',          jam_buka,
    'jam_tutup',         jam_tutup,
    'hari_operasional',  hari_operasional,
    'alamat',            alamat,
    'kota',              kota,
    'no_telp',           no_telp,
    'ongkir_info',       ongkir_info,
    'metode_bayar',      metode_bayar,
    'tagline',           tagline,
    'profile_key',       profile_key,
    'is_active',         is_active
  )
  INTO v_result
  FROM clients
  WHERE client_id = p_client_id
  LIMIT 1;

  RETURN v_result;
END;
$$;

-- ============================================================
-- Verifikasi schema & data
-- ============================================================
SELECT
  client_id,
  name,
  business_name,
  jam_buka || ' - ' || jam_tutup AS jam_operasional,
  alamat,
  no_telp,
  metode_bayar
FROM clients
WHERE is_active = true
ORDER BY client_id;

-- Muat ulang cache schema PostgREST
NOTIFY pgrst, 'reload schema';