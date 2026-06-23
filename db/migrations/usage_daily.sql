-- Usage metering for free-tier rate limiting.
-- Run ONCE in the Supabase SQL editor (Dashboard → SQL → New query → Run).
-- Until this table exists the app fails open (no limiting); after it exists,
-- free-tier caps in api/usage.py take effect.
--
-- NOTE on security: the API connects with the ANON key and authorizes by
-- filtering on user_id in code (same pattern as the existing `inventory` /
-- `profiles` tables). The table is therefore created WITHOUT a restrictive
-- auth.uid() RLS policy, because the server has no per-request JWT context and
-- such a policy would block all writes. If you later harden the project to
-- pass the user JWT to PostgREST, add matching RLS policies to ALL tables.

create table if not exists public.usage_daily (
    user_id  text    not null,
    day      date    not null,
    feature  text    not null,
    count    integer not null default 0,
    primary key (user_id, day, feature)
);
