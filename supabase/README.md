# Supabase relay

This directory contains provider-specific implementation assets for the
FlightMargin mobile relay.

The public application contract is documented in
`docs/mobile-relay-design.md`. Supabase is intentionally treated as a
replaceable backend implementation.

## I-01

`migrations/0001_mobile_relay.sql` creates the first relay schema.

It does not deploy an Edge Function, create a Supabase project, or modify any
production environment.

Before applying the migration:

1. create a dedicated FlightMargin Supabase project;
2. confirm the target project is not shared with unrelated applications;
3. review the SQL migration;
4. configure a server-only HMAC pepper for the future Edge Function;
5. apply the migration through a controlled development workflow.

Clients must never receive the Supabase secret/service-role key.
