-- Per-call LLM token + cost tracking. Run ONCE in the Supabase SQL editor.
-- Until it exists the app fails open (logging is skipped, features keep working).

create table if not exists public.llm_usage (
    id                  text primary key,
    created_at          timestamptz not null default now(),
    user_id             text not null,
    is_demo             boolean not null default false,
    device_label        text,
    provider            text,
    model               text,
    feature             text,
    input_tokens        integer default 0,
    output_tokens       integer default 0,
    total_tokens        integer default 0,
    cached_input_tokens integer default 0,
    cost_usd            double precision default 0,
    latency_ms          integer,
    success             boolean default true,
    error               text
);

create index if not exists llm_usage_created_at on public.llm_usage (created_at);
create index if not exists llm_usage_user        on public.llm_usage (user_id, created_at);

-- The API writes with the anon key (no per-request user JWT context for this
-- analytics table). The admin dashboard also reads with the anon key. The table
-- holds only token counts + metadata (no message content / PII), so a permissive
-- insert+select policy is acceptable for this internal analytics table.
alter table public.llm_usage enable row level security;
drop policy if exists "llm_usage_insert" on public.llm_usage;
drop policy if exists "llm_usage_select" on public.llm_usage;
create policy "llm_usage_insert" on public.llm_usage for insert with check (true);
create policy "llm_usage_select" on public.llm_usage for select using (true);
