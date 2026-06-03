-- ============================================
-- JakHire — Database Schema
-- Execute di Supabase SQL Editor:
-- https://supabase.com/dashboard/project/asfkpvzoxountpmotkop/sql/new
-- ============================================

-- 1. TABEL LISTINGS
CREATE TABLE IF NOT EXISTS listings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'cari_kerja',
  area TEXT NOT NULL,
  budget TEXT DEFAULT '',
  contact TEXT NOT NULL,
  name TEXT DEFAULT '',
  delete_code TEXT NOT NULL,
  user_id UUID REFERENCES auth.users(id),
  email_hash TEXT NOT NULL
);

-- 2. TABEL TRACKING UPLOAD
CREATE TABLE IF NOT EXISTS upload_tracking (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  date DATE DEFAULT CURRENT_DATE,
  count INTEGER DEFAULT 1,
  UNIQUE(user_id, date)
);

-- 3. TABEL LOG SPAM/ACTIVITY
CREATE TABLE IF NOT EXISTS activity_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  email_hash TEXT,
  action TEXT NOT NULL,
  detail TEXT
);

-- ============================================
-- RLS (Row Level Security)
-- ============================================

-- Enable RLS
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_tracking ENABLE ROW LEVEL SECURITY;

-- LISTINGS: siapa aja bisa baca (SELECT)
CREATE POLICY "public_can_select_listings"
  ON listings FOR SELECT
  USING (true);

-- LISTINGS: hanya user terdaftar yang bisa insert
CREATE POLICY "auth_can_insert_listings"
  ON listings FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

-- LISTINGS: update/delete pake delete_code (tanpa auth)
CREATE POLICY "anyone_can_delete_with_code"
  ON listings FOR DELETE
  USING (true);  -- validasi delete_code di aplikasi

-- UPLOAD_TRACKING: user lihat data sendiri
CREATE POLICY "user_can_select_own_upload"
  ON upload_tracking FOR SELECT
  USING (auth.uid() = user_id);

-- UPLOAD_TRACKING: insert/update
CREATE POLICY "user_can_manage_own_upload"
  ON upload_tracking FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_can_update_own_upload"
  ON upload_tracking FOR UPDATE
  USING (auth.uid() = user_id);

-- ============================================
-- AUTO CLEANUP: hapus listing > 7 hari
-- ============================================
CREATE OR REPLACE FUNCTION cleanup_expired_listings()
RETURNS void AS $$
BEGIN
  DELETE FROM listings WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Schedule every hour (via pg_cron or you can run manually)
-- Untuk free tier, jalanin manual atau pake trigger
SELECT cron.schedule('cleanup-listings', '0 * * * *', 'SELECT cleanup_expired_listings()');
-- Note: cron extension mungkin perlu diaktifin di Supabase. Alternatif: jalanin manual.

-- ============================================
-- FUNCTION: cek limit upload hari ini
-- ============================================
CREATE OR REPLACE FUNCTION get_today_upload_count(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
  cnt INTEGER;
BEGIN
  SELECT COALESCE(count, 0) INTO cnt
  FROM upload_tracking
  WHERE user_id = p_user_id AND date = CURRENT_DATE;
  RETURN cnt;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
