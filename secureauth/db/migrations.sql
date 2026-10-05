-- SecureAuth login risk tables.
-- Run this in the Supabase SQL editor. The API key must be allowed to read and write these tables.

create table if not exists login_history (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    timestamp timestamptz not null,
    ip_address text not null,
    device_id text not null,
    location text,
    login_method text not null
);

create index if not exists login_history_user_timestamp_idx
    on login_history (user_id, timestamp desc);

create table if not exists risk_assessments (
    id uuid primary key default gen_random_uuid(),
    event_id text not null,
    user_id text not null,
    risk_score double precision not null,
    risk_level text not null,
    recommended_action text not null,
    reasons jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists risk_assessments_event_id_idx
    on risk_assessments (event_id);

create table if not exists otp_challenges (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    otp_hash text not null,
    expires_at timestamptz not null,
    verified boolean not null default false
);

create index if not exists otp_challenges_user_id_idx
    on otp_challenges (user_id);

create table if not exists security_events (
    id uuid primary key default gen_random_uuid(),
    event_id text not null,
    detail text not null,
    created_at timestamptz not null default now()
);

create index if not exists security_events_event_id_idx
    on security_events (event_id);
