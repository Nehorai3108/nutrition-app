-- Community barcode database
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS barcode_db (
    barcode       TEXT PRIMARY KEY,
    name_he       TEXT NOT NULL,
    name_en       TEXT,
    brand         TEXT,
    image_url     TEXT,
    calories      DOUBLE PRECISION NOT NULL,
    protein       DOUBLE PRECISION NOT NULL DEFAULT 0,
    carbs         DOUBLE PRECISION NOT NULL DEFAULT 0,
    fat           DOUBLE PRECISION NOT NULL DEFAULT 0,
    fiber         DOUBLE PRECISION NOT NULL DEFAULT 0,
    serving_g     DOUBLE PRECISION NOT NULL DEFAULT 100,
    source        TEXT DEFAULT 'community',  -- 'community' | 'off' | 'admin'
    added_by      TEXT,                       -- user_id שהוסיף
    verified      BOOLEAN DEFAULT FALSE,
    times_used    INTEGER DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- אינדקס מהיר
CREATE INDEX IF NOT EXISTS idx_barcode_db_barcode ON barcode_db(barcode);

-- RLS — כולם יכולים לקרוא, רק authenticated יכולים להוסיף
ALTER TABLE barcode_db ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anyone can read barcodes" ON barcode_db;
CREATE POLICY "anyone can read barcodes"
    ON barcode_db FOR SELECT USING (true);

DROP POLICY IF EXISTS "anyone can insert barcodes" ON barcode_db;
CREATE POLICY "anyone can insert barcodes"
    ON barcode_db FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "anyone can update times_used" ON barcode_db;
CREATE POLICY "anyone can update times_used"
    ON barcode_db FOR UPDATE USING (true);
