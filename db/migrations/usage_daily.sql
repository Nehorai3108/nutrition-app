-- Usage metering for free-tier rate limiting.
-- Run ONCE in the Supabase SQL editor (Dashboard → SQL → New query → Run).
-- Until this table exists the app fails open (no limiting); after it exists,
-- free-tier caps in api/usage.py take effect.
--
-- Mirrors the project's existing RLS convention (see meal_balance / profiles):
-- each user can only read/write their own rows via auth.uid()::text = user_id.

CREATE TABLE IF NOT EXISTS usage_daily (
  user_id  TEXT    NOT NULL,
  day      DATE    NOT NULL,
  feature  TEXT    NOT NULL,
  count    INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, day, feature)
);

ALTER TABLE usage_daily ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "usage_daily_all" ON usage_daily;
CREATE POLICY "usage_daily_all" ON usage_daily
  FOR ALL USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);
