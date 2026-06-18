-- ============================================================
-- BiteFit — Supabase table definitions + Row Level Security
-- Run this entire file in the Supabase SQL Editor once.
-- ============================================================

-- ── 1. profiles ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
  user_id          TEXT PRIMARY KEY,
  name             TEXT,
  gender           TEXT,
  date_of_birth    TEXT,
  height_cm        DOUBLE PRECISION,
  weight_kg        DOUBLE PRECISION,
  activity_level   TEXT,
  goal             TEXT,
  meal_preferences JSONB,
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select" ON profiles;
DROP POLICY IF EXISTS "profiles_insert" ON profiles;
DROP POLICY IF EXISTS "profiles_update" ON profiles;

CREATE POLICY "profiles_select" ON profiles
  FOR SELECT USING (auth.uid()::text = user_id);
CREATE POLICY "profiles_insert" ON profiles
  FOR INSERT WITH CHECK (auth.uid()::text = user_id);
CREATE POLICY "profiles_update" ON profiles
  FOR UPDATE USING (auth.uid()::text = user_id);


-- ── 2. food_log ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS food_log (
  id        UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id   TEXT    NOT NULL,
  date      TEXT    NOT NULL,
  food_id   TEXT,
  food_name TEXT,
  grams     DOUBLE PRECISION,
  calories  DOUBLE PRECISION,
  protein   DOUBLE PRECISION,
  carbs     DOUBLE PRECISION,
  fat       DOUBLE PRECISION,
  meal_type TEXT,
  timestamp TEXT,
  entry_id  TEXT    UNIQUE
);

CREATE INDEX IF NOT EXISTS food_log_user_date ON food_log (user_id, date);

ALTER TABLE food_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "food_log_select" ON food_log;
DROP POLICY IF EXISTS "food_log_insert" ON food_log;
DROP POLICY IF EXISTS "food_log_delete" ON food_log;

CREATE POLICY "food_log_select" ON food_log
  FOR SELECT USING (auth.uid()::text = user_id);
CREATE POLICY "food_log_insert" ON food_log
  FOR INSERT WITH CHECK (auth.uid()::text = user_id);
CREATE POLICY "food_log_delete" ON food_log
  FOR DELETE USING (auth.uid()::text = user_id);


-- ── 3. water_data ─────────────────────────────────────────────
-- Stores the entire UserWaterData blob as JSONB (keyed by user)
CREATE TABLE IF NOT EXISTS water_data (
  user_id    TEXT PRIMARY KEY,
  data       JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE water_data ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "water_data_all" ON water_data;

CREATE POLICY "water_data_all" ON water_data
  FOR ALL USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);


-- ── 4. workout_data ───────────────────────────────────────────
-- Stores the entire UserWorkoutData blob as JSONB (keyed by user)
CREATE TABLE IF NOT EXISTS workout_data (
  user_id    TEXT PRIMARY KEY,
  data       JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE workout_data ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "workout_data_all" ON workout_data;

CREATE POLICY "workout_data_all" ON workout_data
  FOR ALL USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);


-- ── 4b. workout_log (row-per-workout, used by the API router) ──
CREATE TABLE IF NOT EXISTS workout_log (
  entry_id         TEXT PRIMARY KEY,
  user_id          TEXT NOT NULL,
  date             TEXT NOT NULL,
  mode             TEXT DEFAULT 'type',
  workout_type     TEXT,
  intensity        TEXT,
  duration_minutes DOUBLE PRECISION,
  distance_km      DOUBLE PRECISION,
  calories_burned  DOUBLE PRECISION,
  timestamp        TEXT
);
CREATE INDEX IF NOT EXISTS workout_log_user_date ON workout_log (user_id, date);

ALTER TABLE workout_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "workout_log_all" ON workout_log;
CREATE POLICY "workout_log_all" ON workout_log
  FOR ALL USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);


-- ── 4c. inventory ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory (
  item_id  TEXT PRIMARY KEY,
  user_id  TEXT NOT NULL,
  name_he  TEXT NOT NULL,
  quantity DOUBLE PRECISION DEFAULT 1,
  unit     TEXT DEFAULT 'יח׳',
  category TEXT DEFAULT 'other',
  added_at TEXT
);
CREATE INDEX IF NOT EXISTS inventory_user ON inventory (user_id);

ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "inventory_all" ON inventory;
CREATE POLICY "inventory_all" ON inventory
  FOR ALL USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);


-- ── 5. daily_summaries ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_summaries (
  user_id TEXT NOT NULL,
  date    TEXT NOT NULL,
  data    JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (user_id, date)
);

ALTER TABLE daily_summaries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "daily_summaries_all" ON daily_summaries;

CREATE POLICY "daily_summaries_all" ON daily_summaries
  FOR ALL USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);
