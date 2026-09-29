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
