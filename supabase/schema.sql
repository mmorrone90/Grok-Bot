-- FrontDesk OS schema for Supabase (Postgres). Mirrors shared/db.py (SQLite fallback).
create table if not exists bots (name text primary key, paused boolean default false);
insert into bots(name) values ('concierge'),('pricer'),('triage'),('scout') on conflict do nothing;
create table if not exists activity (id bigserial primary key, ts timestamptz default now(), bot text references bots(name), kind text, summary text, payload jsonb);
create table if not exists approvals (id bigserial primary key, ts timestamptz default now(), bot text references bots(name), kind text, summary text, payload jsonb, status text default 'pending' check (status in ('pending','approved','rejected')), decided_at timestamptz);
create table if not exists bookings (id bigserial primary key, ts timestamptz default now(), customer text, space text, date date, hours numeric, segment text, community_price numeric, company_price numeric, quoted_price numeric, status text default 'quoted');
create table if not exists tasks (id bigserial primary key, ts timestamptz default now(), title text, category text, urgency text, owner text, source text, status text default 'open');
create table if not exists leads (id bigserial primary key, ts timestamptz default now(), name text, source text, company_number text, score numeric, reason text, event text, pushed_to text);
-- Realtime for the dashboard feed
alter publication supabase_realtime add table activity, approvals;
