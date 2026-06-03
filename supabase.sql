-- ===================== JAKHIRE DATABASE =====================
-- Jalanin di: https://supabase.com/dashboard/project/asfkpvzoxountpmotkop/sql/new
-- =====================

-- 1. TABEL AUTH
CREATE TABLE IF NOT EXISTS auth_codes (
  email TEXT PRIMARY KEY,
  code TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. TABEL LISTINGS (wa & email pisah)
CREATE TABLE IF NOT EXISTS listings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'cari_kerja',
  area TEXT NOT NULL,
  budget TEXT DEFAULT '',
  wa TEXT DEFAULT '',
  email TEXT NOT NULL,
  name TEXT DEFAULT 'Anonim',
  delete_code TEXT NOT NULL
);

-- 3. TABEL TRACKING
CREATE TABLE IF NOT EXISTS upload_tracking (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email TEXT NOT NULL,
  date DATE DEFAULT CURRENT_DATE,
  count INTEGER DEFAULT 1,
  UNIQUE(email, date)
);

-- 4. TABEL LOG
CREATE TABLE IF NOT EXISTS activity_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  email TEXT,
  action TEXT NOT NULL,
  detail TEXT
);

-- RLS
ALTER TABLE auth_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY "all_auth" ON auth_codes FOR ALL USING (true);
CREATE POLICY "all_list" ON listings FOR ALL USING (true);
CREATE POLICY "all_up" ON upload_tracking FOR ALL USING (true);

-- FUNCTION: GET CODE
CREATE OR REPLACE FUNCTION get_or_create_auth_code(p_email TEXT) RETURNS TEXT AS $$
DECLARE ec TEXT; e_ts TIMESTAMPTZ; nc TEXT; ch TEXT:='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; i INT;
BEGIN
  SELECT code,created_at INTO ec,e_ts FROM auth_codes WHERE email=p_email;
  IF FOUND THEN IF e_ts > NOW()-INTERVAL '7 days' THEN RETURN ec; ELSE DELETE FROM auth_codes WHERE email=p_email; END IF; END IF;
  nc:=''; FOR i IN 1..6 LOOP nc:=nc||substr(ch,floor(random()*length(ch)+1)::INT,1); END LOOP;
  INSERT INTO auth_codes(email,code) VALUES(p_email,nc); RETURN nc;
END; $$ LANGUAGE plpgsql SECURITY DEFINER;

-- FUNCTION: VERIFY CODE
CREATE OR REPLACE FUNCTION verify_auth_code(p_email TEXT,p_code TEXT) RETURNS BOOLEAN AS $$
DECLARE sc TEXT; s_ts TIMESTAMPTZ;
BEGIN
  SELECT code,created_at INTO sc,s_ts FROM auth_codes WHERE email=p_email;
  IF NOT FOUND THEN RETURN FALSE; END IF;
  RETURN sc=p_code AND s_ts > NOW()-INTERVAL '7 days';
END; $$ LANGUAGE plpgsql SECURITY DEFINER;

-- FUNCTION: CHECK LIMIT
CREATE OR REPLACE FUNCTION check_upload_limit(p_email TEXT) RETURNS INT AS $$
DECLARE c INT;
BEGIN
  SELECT COALESCE(count,0) INTO c FROM upload_tracking WHERE email=p_email AND date=CURRENT_DATE;
  RETURN c;
END; $$ LANGUAGE plpgsql SECURITY DEFINER;

-- FUNCTION: RECORD UPLOAD
CREATE OR REPLACE FUNCTION record_upload(p_email TEXT) RETURNS VOID AS $$
BEGIN
  INSERT INTO upload_tracking(email,date,count) VALUES(p_email,CURRENT_DATE,1)
  ON CONFLICT(email,date) DO UPDATE SET count=upload_tracking.count+1;
END; $$ LANGUAGE plpgsql SECURITY DEFINER;
