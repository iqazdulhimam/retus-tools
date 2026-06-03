-- ===================== JAKHIRE DATABASE =====================
-- Jalanin di: https://supabase.com/dashboard/project/asfkpvzoxountpmotkop/sql/new
-- =====================

-- 1. TABEL AUTH CODES (login simple pake kode 6 digit)
CREATE TABLE IF NOT EXISTS auth_codes (
  email TEXT PRIMARY KEY,
  code TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. TABEL LISTINGS (iklan)
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
  email TEXT NOT NULL
);

-- 3. TABEL UPLOAD TRACKING (limit 10/hari)
CREATE TABLE IF NOT EXISTS upload_tracking (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email TEXT NOT NULL,
  date DATE DEFAULT CURRENT_DATE,
  count INTEGER DEFAULT 1,
  UNIQUE(email, date)
);

-- 4. TABEL ACTIVITY LOG (monitoring)
CREATE TABLE IF NOT EXISTS activity_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  email TEXT,
  action TEXT NOT NULL,
  detail TEXT
);

-- ===================== RLS =====================
ALTER TABLE auth_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_tracking ENABLE ROW LEVEL SECURITY;

-- Auth codes: semua operasi via anon key (validasi di app)
-- Kita pake security definer function biar aman
CREATE POLICY "public_auth_codes" ON auth_codes FOR ALL USING (true);

-- Listings
CREATE POLICY "public_select_listings" ON listings FOR SELECT USING (true);
CREATE POLICY "public_insert_listings" ON listings FOR INSERT WITH CHECK (true);
CREATE POLICY "public_delete_listings" ON listings FOR DELETE USING (true);

-- Upload tracking
CREATE POLICY "public_upload_tracking" ON upload_tracking FOR ALL USING (true);

-- ===================== FUNCTION: GET OR CREATE CODE =====================
CREATE OR REPLACE FUNCTION get_or_create_auth_code(p_email TEXT)
RETURNS TEXT AS $$
DECLARE
  existing_code TEXT;
  existing_created TIMESTAMPTZ;
  new_code TEXT;
  chars TEXT := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  i INTEGER;
BEGIN
  -- Check if email exists
  SELECT code, created_at INTO existing_code, existing_created
  FROM auth_codes WHERE email = p_email;

  IF FOUND THEN
    -- If within 7 days, return existing code
    IF existing_created > NOW() - INTERVAL '7 days' THEN
      RETURN existing_code;
    ELSE
      -- Expired, delete old
      DELETE FROM auth_codes WHERE email = p_email;
    END IF;
  END IF;

  -- Generate new 6-char code
  new_code := '';
  FOR i IN 1..6 LOOP
    new_code := new_code || substr(chars, floor(random() * length(chars) + 1)::integer, 1);
  END LOOP;

  INSERT INTO auth_codes (email, code) VALUES (p_email, new_code);
  RETURN new_code;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===================== FUNCTION: VERIFY CODE =====================
CREATE OR REPLACE FUNCTION verify_auth_code(p_email TEXT, p_code TEXT)
RETURNS BOOLEAN AS $$
DECLARE
  stored_code TEXT;
  stored_created TIMESTAMPTZ;
BEGIN
  SELECT code, created_at INTO stored_code, stored_created
  FROM auth_codes WHERE email = p_email;

  IF NOT FOUND THEN
    RETURN FALSE;
  END IF;

  -- Check code matches and within 7 days
  IF stored_code = p_code AND stored_created > NOW() - INTERVAL '7 days' THEN
    RETURN TRUE;
  END IF;

  RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===================== FUNCTION: CHECK UPLOAD LIMIT =====================
CREATE OR REPLACE FUNCTION check_upload_limit(p_email TEXT)
RETURNS INTEGER AS $$
DECLARE
  today_count INTEGER;
BEGIN
  SELECT COALESCE(count, 0) INTO today_count
  FROM upload_tracking
  WHERE email = p_email AND date = CURRENT_DATE;
  RETURN today_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===================== FUNCTION: RECORD UPLOAD =====================
CREATE OR REPLACE FUNCTION record_upload(p_email TEXT)
RETURNS VOID AS $$
BEGIN
  INSERT INTO upload_tracking (email, date, count)
  VALUES (p_email, CURRENT_DATE, 1)
  ON CONFLICT (email, date) DO UPDATE
  SET count = upload_tracking.count + 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===================== CLEANUP EXPIRED =====================
-- Hapus auth_codes & listing expired 7 hari (jalanin via cron atau manual)
CREATE OR REPLACE FUNCTION cleanup_expired()
RETURNS void AS $$
BEGIN
  DELETE FROM auth_codes WHERE created_at < NOW() - INTERVAL '7 days';
  DELETE FROM listings WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
