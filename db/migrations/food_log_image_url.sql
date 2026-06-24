-- Add the image_url column to food_log so logged foods keep their thumbnail.
-- Run ONCE in the Supabase SQL editor. Until it runs, food logging still works
-- (the server strips image_url on insert); after it runs, images persist.

ALTER TABLE public.food_log ADD COLUMN IF NOT EXISTS image_url TEXT;
