# Supabase relay

This directory contains provider-specific implementation assets for the
FlightMargin mobile relay.

The public application contract is documented in
`docs/mobile-relay-design.md`. Supabase is intentionally treated as a
replaceable backend implementation.

## I-01

`migrations/20260929173100_mobile_relay.sql` creates the first relay schema.

It does not deploy an Edge Function, create a Supabase project, or modify any
production environment.

Development is local-first: run and validate the Supabase stack from this
repository, commit and push the exact revision to GitHub, then deploy that
revision to the hosted Supabase project.

Before applying the migration to a hosted project:

1. create a dedicated FlightMargin Supabase project;
2. confirm the target project is not shared with unrelated applications;
3. review the SQL migration;
4. configure a server-only HMAC pepper for the future Edge Function;
5. apply the migration through a controlled development workflow.

Clients must never receive the Supabase secret/service-role key.

## I-02

The first local API implementation is the separate Python package in
`relay/`. It uses the existing I-01 schema unchanged and connects with
`FLIGHTMARGIN_RELAY_DATABASE_URL`; credential digests use the server-only
`FLIGHTMARGIN_RELAY_PEPPER`. See `docs/mobile-relay-development.md` for the
loopback-only test workflow. I-02 does not add an Edge Function, pairing
routes, hosted deployment, or production configuration.

## I-03

The Python reference adds five-minute QR/manual pairing, atomic claims,
idempotent retry, exhaustion, and revocation behavior using the I-01 schema.

## I-04A

`functions/relay-v1/` is the production-oriented TypeScript/Deno Supabase Edge
Function. It provides `/health`, host registration, quota upload/read, and
pairing creation/claim while preserving the Python reference contract.
`config.toml` disables Supabase JWT verification for this function because it
validates FlightMargin credentials itself; Supabase Auth accounts are not used.

The function reads only `FLIGHTMARGIN_RELAY_DATABASE_URL`: hosted operation
must provide the Supabase shared transaction-pooler URL on port 6543, while
standalone tests provide the local PostgreSQL URL. It does not fall back to
the built-in direct `SUPABASE_DB_URL`. A module-scope `node-postgres` pool
maintains at most one connection per warm isolate, requires verified TLS for
hosted connections, issues no named/prepared statements, uses explicit
transactions, parameterized SQL, and bounded timeouts, and reads the
server-only `FLIGHTMARGIN_RELAY_PEPPER` (minimum 32 bytes).

`migrations/20260929203000_relay_rate_limits.sql` adds atomic fixed-window
rate-limit buckets keyed by contextual IP HMAC. It does not alter the applied
I-01 migration. Expired buckets are indexed for deletion and may be purged with
`delete from public.relay_rate_limit_buckets where expires_at < now()`.
FlightMargin application code does not persist or log raw client IPs, and the
bucket table stores only contextual HMAC digests. Supabase infrastructure and
its gateway may retain request metadata, including client-IP-related headers,
according to Supabase platform logging and retention; FlightMargin does not
control those infrastructure logs.

Run standalone checks from `functions/relay-v1/` with `deno task check` and
`deno task test`. The manual-only workflow
`.github/workflows/deploy-mobile-relay.yml` documents the eventual deployment
sequence and required GitHub secrets. It has not been run, no hosted project is
linked, and no deployment or secret creation is part of I-04A.
