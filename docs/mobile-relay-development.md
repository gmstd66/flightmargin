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

Application runtime continues to read the database URL and HMAC pepper through
the approved runtime environment variables; do not place either value in a
command, committed file, test output, or application log:

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

Automated Python and Deno database tests use the dedicated test-only variables
`FLIGHTMARGIN_RELAY_TEST_DATABASE_URL` and
`FLIGHTMARGIN_RELAY_TEST_PEPPER`. When either dedicated variable is used, both
must be set; test and runtime credential sources are never mixed. The test
database URL is accepted only when
its parsed host is syntactically `localhost`, in `127.0.0.0/8`, or exactly
`::1`; tests never DNS-resolve a hostname for this decision. For compatibility
with existing local development, tests may fall back to the runtime variables
shown above only when that database URL passes the same loopback check. Missing,
malformed, or non-loopback configuration causes database-backed tests to skip
without displaying connection or credential material. This boundary exists so
a normal developer shell configured for relay runtime cannot accidentally send
automated test traffic to a hosted database.

For the standard disposable local database, configure the test variables for
PostgreSQL on `127.0.0.1:55432`. Runtime application behavior is unchanged, and
the explicitly confirmed hosted I-05B validator continues to use the runtime
database variable in its isolated manual workflow.

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

## I-05A desktop/Linux host client

The packaged host client lives in `app/mobile_relay/`; unlike the reference
server under `relay/`, it is included in normal wheels and the Windows sidecar.
It uses only the Python standard library in addition to existing application
dependencies. QRCode.js is vendored under `app/static/` with its MIT license,
so pairing does not use a CDN.

Relay is opt-in and defaults disabled. Normal enabled operation uses the
production endpoint constant. For local development only, set this before the
application starts:

```text
FLIGHTMARGIN_RELAY_ENDPOINT=http://127.0.0.1:18093
```

The endpoint is configuration/developer input, not a browser setting. HTTP is
accepted only for a loopback host. Never set this variable to the hosted URL
for I-05A tests; leaving it unset is safe only while relay remains disabled.

Persistent non-secret state is in `mobile-relay.json`. Stable host identity is
in `mobile-relay-host.json` beneath the normal FlightMargin application-data
directory. Windows stores only the current-user DPAPI blob; Linux stores the
host credential in the owner-only `0600` file and creates its directory as
`0700` when practical. Do not copy this token into logs, URLs, issue reports,
environment dumps, `quota.db`, or source control. It is a dedicated,
independently revocable FlightMargin credential, not a Codex/OpenAI token.

The local I-05A smoke procedure is:

1. confirm PostgreSQL is listening only at the disposable local target on
   `127.0.0.1:55432` and the committed migrations are present;
2. start `.venv/bin/python -m relay` on `127.0.0.1:18093`;
3. create a temporary application-data directory and configure the loopback
   endpoint through `RelaySettingsStore` or the development override;
4. enable relay, register the generated host, and upload one synthetic approved
   normalized snapshot;
5. explicitly create a pairing, claim it with a fake device credential, and
   read the latest quota with that credential;
6. delete the disposable host row (cascade removes its quota/pairing/device
   records), remove the temporary application directory, and stop the relay;
7. verify nothing listens on `18093`, while protected port `8093` and the
   production service/configuration were unchanged.

The host test suite covers identity persistence and permissions, test-double
Windows protection, endpoint policy, request boundaries, sanitized errors,
retry progression/reset, duplicate suppression, explicit/nonpersistent
pairing, UI expiry behavior, and package inclusion/exclusion. Run it with:

```bash
.venv/bin/python -m pytest -q \
  tests/test_mobile_relay_host.py tests/test_mobile_relay_ui.py \
  tests/test_packaging.py tests/test_desktop.py tests/test_linux_installer.py
```

## I-05B GitHub-hosted validation

`.github/workflows/validate-mobile-relay.yml` is a manual
`workflow_dispatch` gate with `all`, `hosted-rate-limits`, and `windows`
choices. It does not deploy, migrate, publish, upload an artifact, or receive
push/pull-request events. In GitHub Actions run `36783584246`, the hosted job
passed health, both public rate-limit thresholds, and scoped cleanup. The
Windows job reached pytest collection, where its former repository-wide test
selection incorrectly included the separate relay-server development surface;
native DPAPI and package validation therefore remain pending a rerun. The
corrected selection in run `36788962223` collected all 155 intended Python
tests and passed 154; its sole failure was a Linux-only exact-`0600` permission
assertion incorrectly executed on Windows, whose filesystem APIs do not expose
POSIX mode semantics. Native DPAPI and package evidence remains pending the
next rerun.

The Ubuntu job runs `scripts/validate-hosted-mobile-relay.py` against the fixed
hosted relay URL. It checks health, sends small deliberately invalid JSON so
the first 10 host-registration and first 20 pairing-claim requests reach `422`
validation without creating identities or pairing records, and then requires
`429` plus `Retry-After` on requests 11 and 21. Before any HTTP request it
snapshots every composite primary key in `relay_rate_limit_buckets`. Cleanup in
a `finally` path selects the table again and issues parameterized deletes only
for exact `(action, identity_digest, window_started_at)` keys absent from the
original snapshot. It never truncates or deletes a pre-existing key. The job
receives only `SUPABASE_PROJECT_REF` and
`FLIGHTMARGIN_RELAY_DATABASE_URL`, and first applies the existing scoped-role/
pooler URL validation; output excludes connection data, credentials, raw IPs,
IP HMACs, and pepper values.

The Windows job receives no Supabase secret and overrides the relay endpoint
to unreachable loopback for defense in depth. It installs the existing locked
Windows dependencies, runs an explicit application, desktop, mobile-host,
packaging, parity, and release-invariant Python test selection, and uses
`scripts/validate-windows-dpapi.py` with the real current-user
`WindowsDPAPIProtector`. A new identity must contain no plaintext credential;
a second Python process must recover the same host and credential; and another
fresh process must reject a bit-tampered DPAPI blob. All state lives in an
automatically removed temporary directory.

Packaging continues through the canonical `npm run tauri:build` command. The
job builds and verifies the wheel (including every `app/mobile_relay` module
and both vendored QR assets), checks/tests the Rust shell, builds the actual
unsigned NSIS package, and runs an isolated packaged-sidecar health/dashboard/
QR-asset smoke with a missing Codex executable and relay disabled. Nothing is
uploaded or released. A real GitHub-hosted workflow run is still required to
establish native Windows DPAPI evidence and Windows package/runtime evidence.
Real mobile QR/manual pairing and
revocation recovery remain later explicitly authorized validation gates.

## I-04A/I-04B TypeScript hosted relay

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

Integration tests use `FLIGHTMARGIN_RELAY_TEST_DATABASE_URL` and
`FLIGHTMARGIN_RELAY_TEST_PEPPER` against the disposable local PostgreSQL
database, with the loopback-only compatibility fallback described above.
The hosted function uses that same explicit database variable; its value must
be the Supabase shared transaction-pooler connection string on port 6543, not
the built-in direct `SUPABASE_DB_URL`. Hosted connections require TLS. The
HMAC pepper must be at least 32 UTF-8 bytes in both implementations. Neither
database URL nor pepper belongs in source, output, logs, or committed
environment files.

I-04B adds the `flightmargin_relay` login used by the hosted function. The
source-controlled migration owns its non-elevated attributes, grants, and RLS
policies. It deliberately does not own a password. Local integration tests may
continue to use the disposable database administrator URL when they need test
cleanup privileges; least-privilege behavior is separately exercised with
`SET ROLE flightmargin_relay`.

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
I-04B deployment path. It never runs on push or pull request and requires an
explicit `phase` choice. The two phases deliberately have separate secret and
command scopes:

- `phase=prepare` requires `SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_REF`, and
  `SUPABASE_DB_PASSWORD`. It links the project and runs `supabase db push`, but
  cannot set function secrets or deploy `relay-v1`.
- `phase=deploy` requires `SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_REF`,
  `FLIGHTMARGIN_RELAY_PEPPER`, and `FLIGHTMARGIN_RELAY_DATABASE_URL`. It
  validates and installs the runtime secrets and deploys `relay-v1`, but has no
  administrative database password and cannot run migrations.

The deploy phase requires a pepper of at least 32 bytes and a complete shared
transaction-pooler URL whose username is exactly
`flightmargin_relay.<SUPABASE_PROJECT_REF>`, host matches
`*.pooler.supabase.com`, port is `6543`, and password is present. It installs
both function secrets without printing their values.

For the first future hosted deployment, preserve this order:

1. push the reviewed revision;
2. manually run the workflow with `phase=prepare` on that exact revision;
3. allow the committed migrations to create `flightmargin_relay`;
4. have an operator set a strong `flightmargin_relay` password outside Git/CI;
5. construct the transaction-pooler URL as
   `flightmargin_relay.<PROJECT_REF>@*.pooler.supabase.com:6543`;
6. save the complete URL as `FLIGHTMARGIN_RELAY_DATABASE_URL`;
7. configure `FLIGHTMARGIN_RELAY_PEPPER`;
8. manually run the workflow with `phase=deploy` on the **same revision**;
9. perform hosted smoke tests.

The password must be configured once on the hosted database through an
approved out-of-band administrative operation. Do not add it to a migration,
Git, workflow command, or CI variable that tries to create/change the role.
The complete URL exists only as the GitHub function secret.

Both phases check out and report the exact selected commit and install the
official Supabase CLI action. Subsequent deployments normally need only
`phase=deploy`; run `phase=prepare` first when new committed migrations must be
applied. The deploy phase never creates or changes the role password.

Remote smoke tests and any promotion decision remain a human-controlled
follow-up. I-04A/I-04B neither configure those secrets nor run the workflow.

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
