-- Landing-page waitlist. Run ONCE in the Supabase SQL editor.
-- Anonymous visitors can INSERT their email; nobody can read the list via the
-- API (no SELECT policy) — you read it in the Supabase dashboard.

create table if not exists public.waitlist (
  email      text primary key,
  source     text,
  goal       text,
  created_at timestamptz not null default now()
);

alter table public.waitlist enable row level security;

-- allow anonymous signups (insert only)
drop policy if exists "waitlist_insert" on public.waitlist;
create policy "waitlist_insert" on public.waitlist
  for insert with check (true);
