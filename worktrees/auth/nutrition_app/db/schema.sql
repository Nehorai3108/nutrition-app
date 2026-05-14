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
    FOR ALL USING (auth.uid() = user_id);

-- ── User profiles ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
    user_id         UUID    REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    name            TEXT,
    age             INT,
    gender          TEXT,
    weight_kg       FLOAT,
    height_cm       FLOAT,
    activity_level  TEXT,
    goal            TEXT,
    pace            TEXT,
    custom_calories INT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own profile" ON profiles;
CREATE POLICY "own profile" ON profiles
    FOR ALL USING (auth.uid() = user_id);

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
    FOR ALL USING (auth.uid() = user_id);

CREATE TABLE IF NOT EXISTS water_goals (
    user_id         UUID    REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    daily_goal_ml   FLOAT   NOT NULL DEFAULT 2000,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE water_goals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "own water goal" ON water_goals;
CREATE POLICY "own water goal" ON water_goals
    FOR ALL USING (auth.uid() = user_id);

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
    FOR ALL USING (auth.uid() = user_id);
