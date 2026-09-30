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
must provide the Supabase shared transaction-pooler URL on port 6543 with the
dedicated custom-role username, while standalone tests provide the local
PostgreSQL URL. It does not fall back to
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

## I-04B

`migrations/20260930014000_relay_runtime_role.sql` creates and normalizes the
dedicated `flightmargin_relay` login. It has `USAGE` but not `CREATE` on
`public`; `SELECT`, `INSERT`, and `UPDATE` on every relay table; and `DELETE`
only on `relay_rate_limit_buckets`. Explicit role-specific RLS policies expose
the same operations. The role is `NOINHERIT`, cannot bypass RLS, and has no
administrative role, database, replication, or superuser attributes.

The migration intentionally contains no password. For the first authorized
hosted setup:

1. push the reviewed revision;
2. manually run `.github/workflows/deploy-mobile-relay.yml` with
   `phase=prepare` on that exact revision;
3. allow the migrations to create `flightmargin_relay`;
4. have an operator set a strong `flightmargin_relay` password outside Git/CI;
5. construct the transaction-pooler URL as
   `flightmargin_relay.<PROJECT_REF>@*.pooler.supabase.com:6543`;
6. save the complete URL as `FLIGHTMARGIN_RELAY_DATABASE_URL`;
7. configure `FLIGHTMARGIN_RELAY_PEPPER`;
8. manually run the workflow with `phase=deploy` on the **same revision**;
9. perform hosted smoke tests.

Supabase shared-pooler custom-role usernames use `<ROLE>.<PROJECT_REF>`. The
role password is an operational secret configured once on the hosted database
and embedded only in that GitHub secret. CI does not create or change it. The
deployment workflow rejects URLs that do not use the exact relay-role username,
a `*.pooler.supabase.com` host, port `6543`, and a present password.
`phase=prepare` alone has the administrative password and migration command;
`phase=deploy` alone has the runtime secrets and function deployment command.
Subsequent deployments normally require only `phase=deploy`, unless new
migrations must first be applied with `phase=prepare`. I-04B does not apply the
hosted migration, set any password or secret, or deploy the function.
