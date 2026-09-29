# FlightMargin Mobile Relay — Development Workflow

## Principle

The mobile relay follows the same development model as the rest of
FlightMargin:

```text
COXON local checkout
      |
      | develop + test
      v
Git commit on dev/mobile-relay
      |
      | push
      v
GitHub
      |
      | deploy exact committed revision
      v
Hosted Supabase project
```

The hosted Supabase project is a deployment target, not the primary place where
schema or function code is authored.

## Local source of truth

Use the normal FlightMargin development checkout on COXON. Relay work stays on
`dev/mobile-relay` until it is reviewed and intentionally integrated.

The repository owns:

- `supabase/config.toml` after local initialization;
- `supabase/migrations/`;
- `supabase/functions/`;
- safe development seed data;
- relay tests and contract documentation.

Never commit:

- Supabase access tokens;
- database passwords;
- service-role/secret keys;
- Edge Function HMAC pepper;
- live database dumps.

## I-03 local Python relay

The local relay API lives in the separate `relay` Python package. Install its
test dependencies into the development virtual environment:

```bash
.venv/bin/python -m pip install -r requirements-relay-dev.txt
```

Set the database URL and HMAC pepper only through the approved environment
variables; do not place either value in a command, committed file, test output,
or application log:

```text
FLIGHTMARGIN_RELAY_DATABASE_URL
FLIGHTMARGIN_RELAY_PEPPER
```

The pepper must be at least 32 bytes when UTF-8 encoded. The relay rejects a
shorter value without including the value in its error. The local `/health`
route is a simple process-liveness check; it does not query PostgreSQL and must
not be treated as database readiness.

Run focused integration tests against the disposable local relay database:

```bash
.venv/bin/python -m pytest -q \
  tests/test_mobile_relay_schema.py tests/test_mobile_relay_api.py
```

Run the API for local HTTP validation:

```bash
.venv/bin/python -m relay
```

The development entry point is deliberately fixed to `127.0.0.1:18093`.
Do not use port `8093`, a wildcard address, or a hosted Supabase target for
local validation. I-03 tests create unique hosts and pairing sessions, exercise
QR and manual claims through the API, and remove them through host cascade
deletion. Pairing failures for well-formed values deliberately share one
generic `400` response. Malformed input returns `422`; pairing creation keeps
the existing host-authentication `401` response. The `relay/` source is
intentionally excluded from the normal FlightMargin distributable package and
remains runnable from the checkout with `.venv/bin/python -m relay`.

The pairing transaction uses PostgreSQL row locks to serialize claims and
transaction-scoped advisory locks to serialize device/credential identifiers
and manual-code collision checks. QR failures that identify an existing
session commit the increment before returning the generic error. The fifth
failure exhausts the session. An unknown manual code cannot identify which
session should be incremented; deployment-side claim rate limiting is still
required before public exposure.

For the I-03 HTTP smoke test, register a fake host, upload fake quota, create
and claim a pairing, then read quota with the new device credential. Run only
on `127.0.0.1:18093` against local PostgreSQL at `127.0.0.1:55432`, stop the
relay afterward, and confirm that no listener remains.

## I-04A TypeScript hosted relay

The production-oriented Supabase implementation is
`supabase/functions/relay-v1/`. It is a separate TypeScript/Deno implementation
of the same v1 contract; the Python relay remains the local reference. The
TypeScript code connects directly to PostgreSQL because pairing and credential
operations require transactions, row locks, and advisory locks.

For standalone validation on machines where the Supabase Edge Runtime cannot
execute, install Deno in the current user's environment and run:

```bash
cd supabase/functions/relay-v1
deno task check
deno task test
```

Integration tests use `FLIGHTMARGIN_RELAY_DATABASE_URL` and
`FLIGHTMARGIN_RELAY_PEPPER` against the disposable local PostgreSQL database.
The hosted function uses that same explicit database variable; its value must
be the Supabase shared transaction-pooler connection string on port 6543, not
the built-in direct `SUPABASE_DB_URL`. Hosted connections require TLS. The
HMAC pepper must be at least 32 UTF-8 bytes in both implementations. Neither
database URL nor pepper belongs in source, output, logs, or committed
environment files.

The additive migration
`supabase/migrations/20260929203000_relay_rate_limits.sql` owns fixed-window
public rate-limit buckets. It stores only contextual IP HMACs. Expired rows may
be purged safely with:

```sql
delete from public.relay_rate_limit_buckets where expires_at < now();
```

## Local Supabase stack

The Supabase CLI local stack is the development database. It is disposable and
must be reproducible from committed migrations and safe development seed data.

Normal loop:

```bash
git pull
supabase start
supabase db reset
# develop/test
git add supabase/ docs/ tests/
git commit
git push
```

After another developer or branch adds migrations, pull Git and run
`supabase db reset` so the local database is rebuilt from the repository.

Do not expose the local Supabase development stack to the public internet. It
is a development service, not the relay production endpoint.

## Manual hosted deployment rule

The manual-only `.github/workflows/deploy-mobile-relay.yml` is the sole prepared
I-04A deployment path. It never runs on push. Configure these GitHub repository
secrets before an authorized deployment:

- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_PROJECT_REF`
- `SUPABASE_DB_PASSWORD`
- `FLIGHTMARGIN_RELAY_PEPPER` (at least 32 bytes)
- `FLIGHTMARGIN_RELAY_DATABASE_URL` (the shared transaction-pooler URL on port
  6543)

`SUPABASE_DB_PASSWORD` is available only to the CLI link/migration steps. The
workflow installs both `FLIGHTMARGIN_RELAY_PEPPER` and
`FLIGHTMARGIN_RELAY_DATABASE_URL` as function secrets without printing their
values.

Once a revision is tested locally, pushed to GitHub, and deployment is
explicitly approved, manually select that exact revision and run the workflow.
It will:

1. check out the selected exact commit on a GitHub-hosted Ubuntu runner;
2. install the official Supabase CLI action;
3. link the dedicated hosted project;
4. apply committed migrations with `supabase db push`;
5. set `FLIGHTMARGIN_RELAY_PEPPER` and
   `FLIGHTMARGIN_RELAY_DATABASE_URL` in the function secret store;
6. deploy `relay-v1` and report the deployed commit SHA.

Remote smoke tests and any promotion decision remain a human-controlled
follow-up. I-04A neither configures those secrets nor runs the workflow.

Do not make ad-hoc schema edits in the hosted Supabase Dashboard. Remote schema
changes must originate from repository migrations so Git remains canonical.

## Three database roles

### 1. Local development database

Purpose: development and tests.

- recreated freely with `supabase db reset`;
- contains only safe development/test data;
- never treated as a backup of production;
- reproducible from Git.

### 2. Hosted Supabase relay database

Purpose: live/staging relay operation.

- stores latest relay state and pairing/device records;
- changed only through committed migrations;
- backed up to COXON.

### 3. COXON relay backup archive

Purpose: independent disaster-recovery copy of hosted relay data.

Planned path:

```text
/srv/flightmargin/backups/supabase/
```

The backup job will create timestamped logical data dumps from the linked
hosted database. The schema is versioned in Git, so recovery consists of:

1. provision a clean Postgres/Supabase target;
2. apply the Git migrations;
3. restore the selected data dump;
4. rotate/reconfigure server secrets as required;
5. validate host/device access.

Initial retention target:

- 14 daily backups;
- 8 weekly backups.

Backup files must be excluded from Git, readable only by the backup owner, and
kept separate from the development database. Once the hosted project exists,
the backup job should use an unattended credential stored outside the
repository in a restricted system location.

## Backup verification

A backup is not considered reliable merely because a dump command succeeded.
Periodically restore a selected dump into an isolated local database and run
basic integrity checks:

- expected relay tables exist;
- row counts are plausible;
- foreign keys validate;
- revoked credentials stay revoked;
- quota rows resolve to existing hosts.

## Why the live copy is separate from development

Restoring live relay data directly into the normal development database would
introduce state that migrations and seed files cannot reproduce, and could
place security-sensitive credential digests into routine development workflows.

Keeping a separate backup/mirror preserves both goals:

- deterministic local development;
- an independent copy of hosted operational data.

## Environment boundaries

| Component | Role | Contains operational data? |
| --- | --- | --- |
| Python `relay/` | Local reference implementation | Only when pointed at the disposable local database |
| TypeScript `supabase/functions/relay-v1/` | Hosted implementation, locally testable with Deno | Only after an authorized hosted deployment |
| Local PostgreSQL on COXON/developer machine | Disposable migration and integration-test database | No hosted operational state |
| Hosted Supabase PostgreSQL | Future operational relay database | Yes, after deployment |
| GitHub-hosted Ubuntu runner | Ephemeral manual deployment executor | No retained database or backup |
| COXON backup archive | Future restricted disaster-recovery archive | Logical copies of hosted state; never a development database |
