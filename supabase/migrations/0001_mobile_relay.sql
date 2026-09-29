-- FlightMargin mobile relay schema v1
-- Supabase/Postgres migration.
--
-- Client applications must not access these tables directly. They communicate
-- only with the FlightMargin Edge Function. anon/authenticated grants are
-- explicitly revoked as defense in depth.

begin;

create table public.relay_hosts (
    id uuid primary key,
    display_name text not null
        check (char_length(display_name) between 1 and 120),
    platform text not null
        check (char_length(platform) between 1 and 32),
    app_version text,
    created_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    revoked_at timestamptz
);

create table public.relay_host_credentials (
    id uuid primary key,
    host_id uuid not null
        references public.relay_hosts(id) on delete cascade,
    token_digest text not null unique
        check (token_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    last_used_at timestamptz,
    revoked_at timestamptz
);

create table public.relay_devices (
    id uuid primary key,
    host_id uuid not null
        references public.relay_hosts(id) on delete cascade,
    display_name text not null
        check (char_length(display_name) between 1 and 120),
    platform text not null
        check (char_length(platform) between 1 and 32),
    created_at timestamptz not null default now(),
    last_seen_at timestamptz,
    revoked_at timestamptz
);

create table public.relay_device_credentials (
    id uuid primary key,
    device_id uuid not null
        references public.relay_devices(id) on delete cascade,
    token_digest text not null unique
        check (token_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    last_used_at timestamptz,
    revoked_at timestamptz
);

create table public.relay_pairing_sessions (
    id uuid primary key,
    host_id uuid not null
        references public.relay_hosts(id) on delete cascade,
    qr_secret_digest text not null
        check (qr_secret_digest ~ '^[0-9a-f]{64}$'),
    manual_code_digest text not null
        check (manual_code_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    attempts integer not null default 0
        check (attempts >= 0),
    max_attempts integer not null default 5
        check (max_attempts between 1 and 20),
    claimed_at timestamptz,
    claimed_device_id uuid
        references public.relay_devices(id) on delete set null,
    check (expires_at > created_at),
    check (attempts <= max_attempts)
);

create table public.relay_quota_state (
    host_id uuid primary key
        references public.relay_hosts(id) on delete cascade,
    schema_version smallint not null default 1
        check (schema_version >= 1),
    sampled_at timestamptz not null,
    received_at timestamptz not null default now(),
    five_hour_used numeric(5,2)
        check (
            five_hour_used is null
            or five_hour_used between 0 and 100
        ),
    five_hour_reset_at timestamptz,
    weekly_used numeric(5,2)
        check (
            weekly_used is null
            or weekly_used between 0 and 100
        ),
    weekly_reset_at timestamptz,
    plan_type text,
    reset_credits_available integer
        check (
            reset_credits_available is null
            or reset_credits_available >= 0
        ),
    credits_balance numeric(20,4)
        check (
            credits_balance is null
            or credits_balance >= 0
        ),
    spend_control_reached boolean,
    rate_limit_reached_type text,
    collector_state text not null default 'ok'
        check (collector_state in ('ok', 'degraded', 'error')),
    collector_message_code text
);

create index relay_host_credentials_host_active_idx
    on public.relay_host_credentials(host_id)
    where revoked_at is null;

create index relay_devices_host_active_idx
    on public.relay_devices(host_id)
    where revoked_at is null;

create index relay_device_credentials_device_active_idx
    on public.relay_device_credentials(device_id)
    where revoked_at is null;

create index relay_pairing_sessions_host_active_idx
    on public.relay_pairing_sessions(host_id, expires_at)
    where claimed_at is null;

create index relay_pairing_sessions_manual_code_idx
    on public.relay_pairing_sessions(manual_code_digest)
    where claimed_at is null;

alter table public.relay_hosts enable row level security;
alter table public.relay_host_credentials enable row level security;
alter table public.relay_devices enable row level security;
alter table public.relay_device_credentials enable row level security;
alter table public.relay_pairing_sessions enable row level security;
alter table public.relay_quota_state enable row level security;

revoke all privileges on table public.relay_hosts
    from anon, authenticated;
revoke all privileges on table public.relay_host_credentials
    from anon, authenticated;
revoke all privileges on table public.relay_devices
    from anon, authenticated;
revoke all privileges on table public.relay_device_credentials
    from anon, authenticated;
revoke all privileges on table public.relay_pairing_sessions
    from anon, authenticated;
revoke all privileges on table public.relay_quota_state
    from anon, authenticated;

grant select, insert, update, delete
    on table public.relay_hosts
    to service_role;
grant select, insert, update, delete
    on table public.relay_host_credentials
    to service_role;
grant select, insert, update, delete
    on table public.relay_devices
    to service_role;
grant select, insert, update, delete
    on table public.relay_device_credentials
    to service_role;
grant select, insert, update, delete
    on table public.relay_pairing_sessions
    to service_role;
grant select, insert, update, delete
    on table public.relay_quota_state
    to service_role;

comment on table public.relay_hosts is
    'FlightMargin relay hosts. Direct client table access is forbidden.';
comment on table public.relay_devices is
    'FlightMargin paired mobile devices. Direct client table access is forbidden.';
comment on table public.relay_quota_state is
    'Latest normalized FlightMargin quota snapshot per host; no remote history in v1.';

commit;
