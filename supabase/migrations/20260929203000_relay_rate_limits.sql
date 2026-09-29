-- Database-backed fixed-window limits for unauthenticated relay endpoints.
-- Only the contextual HMAC of an IP identity is stored; raw addresses are
-- never persisted. Expired rows can be removed without affecting live limits.

begin;

create table public.relay_rate_limit_buckets (
    action text not null
        check (action in ('host-registration', 'pairing-claim')),
    identity_digest text not null
        check (identity_digest ~ '^[0-9a-f]{64}$'),
    window_started_at timestamptz not null,
    expires_at timestamptz not null,
    request_count integer not null default 1
        check (request_count >= 1),
    primary key (action, identity_digest, window_started_at),
    check (expires_at > window_started_at)
);

create index relay_rate_limit_buckets_expiry_idx
    on public.relay_rate_limit_buckets(expires_at);

alter table public.relay_rate_limit_buckets enable row level security;

revoke all privileges on table public.relay_rate_limit_buckets
    from anon, authenticated;

grant select, insert, update, delete
    on table public.relay_rate_limit_buckets
    to service_role;

comment on table public.relay_rate_limit_buckets is
    'Fixed-window public relay rate limits keyed only by contextual IP HMAC.';

commit;
