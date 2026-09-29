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

## Remote deployment rule

Once a revision is tested locally and pushed to GitHub:

1. link the checkout to the dedicated FlightMargin Supabase development/staging
   project;
2. verify migration history;
3. run `supabase db push`;
4. deploy Edge Functions from the same Git commit;
5. perform remote smoke tests;
6. only then promote the reviewed change toward production.

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
