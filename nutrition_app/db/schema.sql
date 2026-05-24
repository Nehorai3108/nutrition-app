-- ============================================================
-- BiteFit — Supabase schema
-- Run once in Supabase: SQL Editor → New query → paste & run
-- ============================================================

-- ── Food log ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS food_log (
    id          UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID    REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    date        DATE    NOT NULL,
    food_id     TEXT,
    food_name   TEXT    NOT NULL,
    grams       FLOAT   NOT NULL,
    calories    FLOAT   NOT NULL DEFAULT 0,
    protein     FLOAT   NOT NULL DEFAULT 0,
    carbs       FLOAT   NOT NULL DEFAULT 0,
    fat         FLOAT   NOT NULL DEFAULT 0,
    meal_type   TEXT    NOT NULL DEFAULT 'lunch',
    entry_id    TEXT    UNIQUE,
    timestamp   TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE food_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own food log" ON food_log;
CREATE POLICY "own food log" ON food_log
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

-- ── User profiles ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
    user_id            UUID    REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    name               TEXT,
    age                INT,                 -- legacy, unused (use date_of_birth)
    gender             TEXT,
    date_of_birth      DATE,
    weight_kg          FLOAT,
    height_cm          FLOAT,
    activity_level     TEXT,
    goal               TEXT,
    pace               TEXT,
    weekly_change_kg   FLOAT,
    target_weight_kg   FLOAT,
    weeks_to_goal      INT,
    custom_calories    INT,                 -- legacy, unused
    meal_preferences   JSONB,
    updated_at         TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own profile" ON profiles;
CREATE POLICY "own profile" ON profiles
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

-- ── Water log ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS water_log (
    id          UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID    REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    water_id    TEXT    UNIQUE,
    date        DATE    NOT NULL,
    amount_ml   FLOAT   NOT NULL,
    source      TEXT    DEFAULT 'water',
    notes       TEXT,
    timestamp   TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE water_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own water log" ON water_log;
CREATE POLICY "own water log" ON water_log
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE TABLE IF NOT EXISTS water_goals (
    user_id         UUID    REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    daily_goal_ml   FLOAT   NOT NULL DEFAULT 2000,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE water_goals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own water goal" ON water_goals;
CREATE POLICY "own water goal" ON water_goals
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

-- ── Workouts ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workouts (
    id              UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         UUID    REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    workout_id      TEXT    UNIQUE,
    date            DATE    NOT NULL,
    workout_type    TEXT,
    duration_min    INT,
    calories_burned FLOAT,
    notes           TEXT,
    timestamp       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE workouts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own workouts" ON workouts;
CREATE POLICY "own workouts" ON workouts
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

-- ── Daily summaries ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_summaries (
    id              UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         UUID    REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    date            DATE    NOT NULL,
    summary_json    JSONB   NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

ALTER TABLE daily_summaries ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own daily summary" ON daily_summaries;
CREATE POLICY "own daily summary" ON daily_summaries
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

-- ── Inventory ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory (
    id              UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         UUID    REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    food_id         TEXT    NOT NULL,
    name_he         TEXT,
    quantity_g      FLOAT   NOT NULL DEFAULT 0,
    unit            TEXT    DEFAULT 'gram',
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, food_id)
);

ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own inventory" ON inventory;
CREATE POLICY "own inventory" ON inventory
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

-- ── User workout data (blob form — matches UserWorkoutData model) ────
-- Stores both the weekly plan and the daily log as a single JSONB blob
-- per user. Simpler than decomposing for the demo timeline.
CREATE TABLE IF NOT EXISTS user_workout_data (
    user_id     UUID    REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    blob        JSONB   NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_workout_data ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own workout data" ON user_workout_data;
CREATE POLICY "own workout data" ON user_workout_data
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

-- ── User water data (blob form — matches UserWaterData model) ────────
CREATE TABLE IF NOT EXISTS user_water_data (
    user_id     UUID    REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    blob        JSONB   NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_water_data ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own water data" ON user_water_data;
CREATE POLICY "own water data" ON user_water_data
    FOR ALL USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

-- ── Idempotent migrations for existing Supabase projects ─────
-- Re-running schema.sql on a project where `profiles` already exists
-- without the newer columns: add them in-place. Safe to run multiple times.
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS date_of_birth     DATE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS pace              TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS weekly_change_kg  FLOAT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS target_weight_kg  FLOAT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS weeks_to_goal     INT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS meal_preferences  JSONB;

-- Calm Mode toggles for user_meal_preferences
ALTER TABLE user_meal_preferences ADD COLUMN IF NOT EXISTS show_streaks        boolean DEFAULT false;
ALTER TABLE user_meal_preferences ADD COLUMN IF NOT EXISTS daily_notifications  boolean DEFAULT false;
ALTER TABLE user_meal_preferences ADD COLUMN IF NOT EXISTS weekly_summary       boolean DEFAULT false;
