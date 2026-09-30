# FlightMargin — Project Status

Updated: 2026-09-30

Branch: `dev/mobile-host-integration`

This is the primary continuity record. Read it with `AGENTS.md` and verify it
against the working tree and Git history before making changes.

## Product state

FlightMargin is a lightweight, local-first monitor for OpenAI Codex usage
limits, pacing, resets, purchased credits, and history. It is the public
identity adopted in milestone 6.20D.1; the prior internal identity was Codex
Quota Monitor.

The canonical version is `0.3.0-beta.1` in `app/version.py`. Generated Cargo
and Tauri versions match it. Python distribution metadata uses the equivalent
PEP 440 form `0.3.0b1`. The beta feature set is frozen.

The public repository is `https://github.com/gmstd66/flightmargin`. FlightMargin
`0.3.0-beta.1` is published there as a GitHub prerelease. Beta 1 is
intentionally unsigned; code signing is not a Beta 1 gate. Auto-update is
deferred. About exposes Source Code and Report an Issue actions. Sponsor links
remain deferred and absent.

The `0.3.0-beta.1` release candidate passed final owner acceptance in milestone
6.21A-F and was published under the owner's separate milestone 6.21B approval.

FlightMargin is licensed `AGPL-3.0-or-later`; the standard GNU AGPL v3 text is
present in `LICENSE`. Third-party license notices remain separately inventoried.

Unofficial community tool. Not affiliated with or endorsed by OpenAI.

## Architecture

The core local architecture is retained and the relay is an optional side path:

```text
browser / CLI -> FastAPI or CLI -> Codex app-server JSON-RPC
                              -> normalization and metrics
                              -> SQLite history -> dashboard and tray
```

- `app/main.py`: FastAPI app, API routes, and collector lifecycle.
- `app/adapters/codex_stdio.py`: persistent `codex app-server --stdio` client.
- `app/core`: configuration, environment discovery, quota normalization, and
  derived pacing metrics.
- `app/storage/sqlite_store.py`: local SQLite history.
- `app/mobile_relay/`: optional host identity, relay configuration/transport,
  latest-only synchronization, retry state, and pairing coordination.
- `app/cli.py`: `flightmargin` CLI and legacy `codex-quota` alias.
- `app/systemd.py`: systemd unit rendering.
- `desktop/`: Tauri 2 shell, PyInstaller sidecar build, tray/startup behavior,
  and current-user NSIS packaging.

The Windows shell communicates with its sidecar on an OS-assigned loopback
port. The Linux browser deployment has no application-level authentication and
must stay on localhost or a trusted private network.

## Mobile companion relay — I-01 through I-04B

The approved mobile-companion architecture uses a central Supabase relay so the
iPhone requires no VPN, port forwarding, third-party user account, router
configuration, or direct connection to the host. The desktop/Linux agent
uploads only normalized quota state; OpenAI/Codex credentials, prompts,
transcripts, source code, agent output, and local history remain on the host.

I-01 is specified in `docs/mobile-relay-design.md` with a provider-independent
FlightMargin API contract and an initial Supabase migration at
`supabase/migrations/20260929173100_mobile_relay.sql`. Clients use revocable
FlightMargin host/device credentials and never receive Supabase
secret/service-role credentials. Relay tables have RLS enabled and direct
`anon`/`authenticated` grants revoked. Pairing uses a five-minute one-time
QR secret or high-entropy manual code. The relay stores one latest quota row
per host; remote history, APNs, and iOS UI implementation remain deferred.

Development for this work is isolated on `dev/mobile-relay`; it does not
modify the published Beta 1 tag. Relay development is local-first on COXON,
with Git/GitHub as the canonical schema and code source. Hosted Supabase is a
deployment target. A separate scheduled COXON backup archive will retain
logical copies of hosted relay data without mixing live state into the
disposable development database.

I-02 adds separate `relay/` FastAPI source for the first working local API.
It implements health, accountless idempotent host registration, authenticated
monotonic quota upload, and authenticated paired-device quota retrieval. The
API reads only `FLIGHTMARGIN_RELAY_DATABASE_URL` and
`FLIGHTMARGIN_RELAY_PEPPER`; raw credential secrets are parsed in memory,
contextually HMACed, and never stored. The pepper must be at least 32 bytes.
Host/device revocation is enforced on every authenticated request, with
constant-time digest checks after credential-ID lookup and row locking. Relay
PostgreSQL connects use a five-second timeout. The versioned registration and
quota-read responses, immutable idempotent-registration metadata, strict input
validation, and bounded public strings are covered by tests. The local entry
point binds only to `127.0.0.1:18093` and is separate from the
browser/dashboard API and its configuration. Its liveness endpoint does not
claim PostgreSQL readiness.

The relay is a local reference/test implementation, so setuptools package
discovery remains limited to `app` and excludes `relay`; the relay still runs
from the source checkout with `.venv/bin/python -m relay`.

I-03 implements host-authenticated `POST /v1/pairings` and accountless
`POST /v1/pairings/claim`. The relay generates a UUID, 32-byte QR secret, and
10-character Crockford Base32 manual code, returns token/manual/deep-link
values, and stores only contextual HMAC digests. Sessions expire exactly five
minutes after creation and allow five session-addressable failed attempts.
Claims use row locks and transactions, create the device and credential
atomically, support same-device/same-credential retry, prevent a different
claimant from reusing the session, and preserve host/device revocation.

The existing I-01 migration supports I-03 and required no change. Focused
tests cover strict validation, secret absence, expiry/exhaustion, both claim
methods, idempotency, immediate quota access, revocation, and concurrent
double claims. A manual code that matches no digest cannot identify a target
session to increment; it receives the same generic error, and planned
deployment-side per-IP claim rate limiting remains required before public
exposure. No Edge Function, QR rendering, iPhone UI, hosted Supabase
deployment, production service, or production data change is part of I-03.

I-04A adds the production-oriented `relay-v1` Supabase Edge Function as a
separate TypeScript/Deno implementation of the complete current relay contract.
It uses FlightMargin credentials without Supabase Auth, a module-scope
`node-postgres` pool capped at one verified-TLS connection per hosted warm
isolate, unnamed parameterized SQL, bounded connection/query behavior,
constant-time digest comparisons, and explicit multi-query transactions that
preserve the I-02/I-03 row/advisory locking and revocation semantics. It reads
only `FLIGHTMARGIN_RELAY_DATABASE_URL`; hosted operation requires the Supabase
shared transaction-pooler URL with the dedicated custom-role username on port
6543 and never falls back to the built-in direct `SUPABASE_DB_URL`.
`supabase/config.toml` explicitly sets
`verify_jwt = false`. The Python implementation remains the local reference.

The additive I-04A migration creates `relay_rate_limit_buckets`. Atomic
fixed-window upserts enforce 10 host registrations per IP-HMAC per 60 minutes
and 20 pairing claims per IP-HMAC per five minutes. The function prefers the
gateway `cf-connecting-ip`, falls back to `x-real-ip`, and shares one `unknown`
identity when neither is available. `relay_rate_limit_buckets` stores only a
dedicated contextual HMAC, not the raw client IP. FlightMargin application
code does not persist or log raw client IPs. Supabase infrastructure and its
gateway may retain request metadata, including client-IP-related headers,
according to Supabase platform logging and retention; FlightMargin does not
control those infrastructure logs. Expired buckets are indexed and purged
during checks. QR session failures retain the five-attempt behavior, while
unknown manual codes remain protected by their entropy plus the mandatory
per-IP claim limit.

Public-edge handling is explicit and bounded: exact routes/methods, required
JSON content type, a 16 KiB body maximum, strict contract fields/types, no CORS
policy, generic internal errors, and safe request-ID-only failure logging. Deno
tests run without the unsupported local Supabase Edge Runtime and cover shared
Python/TypeScript crypto vectors, routing/validation/error safety, and live
PostgreSQL registration, authentication, quota, pairing, revocation,
expiry/exhaustion, and rate limiting.

The GitHub-hosted Ubuntu workflow is manual-only and explicitly two-phase.
`phase=prepare` requires the access token, project ref, and administrative
database password; it checks out the exact selected commit, links the project,
applies committed migrations, and reports the SHA, but cannot read runtime
secrets or deploy. `phase=deploy` requires the access token, project ref,
server-only pepper, and dedicated-role transaction-pooler URL; it validates and
sets those two runtime secrets without printing them, deploys `relay-v1`, and
reports the SHA, but cannot read the administrative password or apply
migrations. I-04A creates none of those secrets and performs no push, hosted
project link, workflow run, deployment, production change, or COXON backup
operation.

Local I-04A validation passed 185 Python tests, 15 standalone Deno tests with
live disposable-PostgreSQL coverage, Deno format/lint/type checks, a clean
I-01-plus-I-04A migration replay, workflow syntax checks, and wheel build and
artifact verification. The COXON CPU cannot run the local Supabase Edge
Runtime, so gateway behavior, hosted secret injection and transaction-pooler
TLS connectivity, migration application through the Supabase CLI, and remote
smoke tests remain deployment-time validation gates.

I-04B prepares least-privilege hosted database access without touching hosted
Supabase. The additive migration
`supabase/migrations/20260930014000_relay_runtime_role.sql` creates the
`flightmargin_relay` login as `NOINHERIT`, with no superuser, database/role
creation, replication, or RLS-bypass attributes. It grants only `USAGE` on
`public`; `SELECT`, `INSERT`, and `UPDATE` on all seven relay tables; and
`DELETE` on `relay_rate_limit_buckets`. Explicit role-specific policies permit
exactly those commands through the existing RLS boundaries. The workflow now
requires the shared Transaction Pooler URL to use
`flightmargin_relay.<SUPABASE_PROJECT_REF>` on a `*.pooler.supabase.com` host
and port `6543`.

The password remains deliberately outside the schema and CI. The exact first
deployment sequence is: (1) push the reviewed revision; (2) manually run
`phase=prepare` on that exact revision; (3) let migrations create
`flightmargin_relay`; (4) have an operator set a strong role password outside
Git/CI; (5) construct the transaction-pooler URL as
`flightmargin_relay.<PROJECT_REF>@*.pooler.supabase.com:6543`; (6) save the
complete URL as `FLIGHTMARGIN_RELAY_DATABASE_URL`; (7) configure
`FLIGHTMARGIN_RELAY_PEPPER`; (8) manually run `phase=deploy` on the **same
revision**; and (9) perform hosted smoke tests. Subsequent deployments normally
need only `phase=deploy`, unless new migrations must first be applied with
`phase=prepare`. No hosted migration, password change, secret update, push, or
deployment is part of I-04B.

Local I-04B validation passed 194 Python tests, 15 Deno tests, Deno format,
lint, and type checks, and 17 focused schema/least-privilege/workflow tests
(including six positive/negative URL cases) against a fresh PostgreSQL 17
replay. The full migration chain applied cleanly, the I-04B migration replayed
idempotently, and the focused current-tree secret scan found no high-confidence
secret.

I-05A adds opt-in desktop/Linux host integration on
`dev/mobile-host-integration`. Relay remains disabled by default. When enabled,
the application creates one stable host identity, idempotently registers it,
and sends only the latest successful normalized quota sample. The collector,
SQLite history, dashboard, and tray continue normally during relay failure or
disablement. Duplicate sample notifications are suppressed, concurrent relay
operations are serialized, and retry uses bounded 2/5/15/30/60/300-second
steps that reset on success.

`app/mobile_relay/config.py` owns persisted opt-in state and endpoint policy;
`identity.py` owns the stable UUID/credential and native Windows DPAPI or Linux
owner-only `0600` storage; `client.py` owns five-second verified-TLS standard-
library transport with redirects rejected; and `sync.py` owns registration,
the exact allowlisted v1 serializer, latest-only upload, pairing, and sanitized
status/backoff. The browser can toggle only `enabled`; it cannot supply an
endpoint. Production uses the hosted HTTPS constant, while local I-05A work
uses the developer-only `FLIGHTMARGIN_RELAY_ENDPOINT` override and permits
cleartext only on loopback.

Settings includes Mobile Relay state, last successful sync, and an explicit
**Pair mobile device** action. A five-minute manual code, countdown, and QR of
the returned deep link are held only in browser memory/DOM and cleared on
expiry, disablement, or replacement. Vendored MIT QRCode.js avoids runtime CDN
or Python dependencies. The UI does not claim an iPhone app exists. Host and
pairing credentials never enter `quota.db`, logs, HTML source, or persisted
pairing state.

I-05A automated validation passes 223 Python tests, including live disposable-
PostgreSQL relay contract tests, plus JavaScript syntax and wheel/package
checks. A process-level smoke against only `127.0.0.1:18093` and PostgreSQL
`127.0.0.1:55432` registered a disposable host, uploaded an approved synthetic
snapshot, created and claimed a pairing with a fake device, and read back the
latest quota. Its host cascade and temporary application data were removed and
the listener stopped. No hosted Supabase request/change or production
FlightMargin change occurred.

I-05B now has a manual-only GitHub Actions validation gate. Run `36783584246`
passed hosted health, both public rate-limit thresholds, and scoped cleanup.
Its isolated Ubuntu job snapshots the complete
`relay_rate_limit_buckets` primary-key set, proves the hosted health and 10/20
public thresholds with invalid non-persisting payloads, and deletes only the
exact bucket keys created after the snapshot. Its Windows job receives no
Supabase secrets or hosted endpoint, exercises real current-user DPAPI across
fresh Python processes (including tamper rejection), runs an explicit
application/desktop/mobile-host test selection against the locked Windows
dependencies, verifies wheel inclusion of all mobile-relay/QR assets,
builds through canonical `npm run tauri:build`, and smokes the packaged
sidecar with isolated state and no real Codex quota window. No artifact is
uploaded or released. The Windows job in run `36783584246` reached pytest but
the former repository-wide selection collected separate relay-server tests
whose development dependencies are intentionally absent. Native DPAPI and
Windows package evidence remain pending a rerun. The corrected selection in
run `36788962223` collected all 155 intended Python tests and passed 154. Its
only failure was a Linux-only exact-`0600` permission assertion incorrectly
executed on Windows, which does not provide POSIX mode-bit semantics. Native
DPAPI and package evidence remains pending the next rerun. Real mobile QR/manual
pairing, revocation/authentication recovery, and remote device-management UX
remain later explicit gates.

Current local I-05B tooling validation passes 210 Python tests with 38
database-backed tests skipped when relay test credentials are deliberately
absent, plus 17 Deno tests with 3 database integrations ignored. With dedicated
loopback test configuration, 80 focused Python relay/configuration tests and all
20 Deno tests pass against PostgreSQL at `127.0.0.1:55432`. The Linux wheel
builds and passes the expanded release-content verifier. Native DPAPI,
PyInstaller/Tauri/NSIS, and hosted threshold results remain unclaimed until the
manual workflow runs.

After the I-05B validation incident, relay automated-test configuration is
separated from application runtime configuration. Central Python and Deno test
helpers prefer `FLIGHTMARGIN_RELAY_TEST_DATABASE_URL` and
`FLIGHTMARGIN_RELAY_TEST_PEPPER`; both reject every database URL whose parsed
host is not syntactically `localhost`, in `127.0.0.0/8`, or exactly `::1`.
Dedicated test variables are required as a pair and are never mixed with
runtime credential sources. Existing runtime variables remain a compatibility
fallback only when the runtime database target is loopback. The check performs
no DNS lookup and skip output contains no URL, hostname, username, password, or
pepper. A fake `.invalid` runtime target passed the full Python and Deno suites
with traced connection syscalls proving no attempt to its relay port.
Application runtime, deployment, and the explicitly confirmed hosted I-05B
validator retain their existing configuration behavior.

## Public identity and compatibility

- Browser, Settings/About, tray, installer, Start Menu, CLI output, workflow
  artifacts, and current documentation use FlightMargin.
- Tauri product name is `FlightMargin`; bundle identifier is
  `io.github.gmstd66.flightmargin`; the Rust package/main executable is
  `flightmargin-desktop`.
- Python distribution name is `flightmargin`; Python imports remain under
  `app` to avoid a cosmetic module rewrite.
- New Linux installs default to CLI `flightmargin` and service
  `flightmargin.service`. The `codex-quota` command remains an alias, and
  explicit legacy service/CLI configurations remain supported.
- Existing `CODEX_QUOTA_*` configuration variables, the
  `codex-quota-backend` sidecar name, internal browser channel names, and the
  sidecar readiness protocol remain stable compatibility identifiers.
- The public GitHub repository is `gmstd66/flightmargin`; its issue destination
  is `https://github.com/gmstd66/flightmargin/issues`.

See `docs/flightmargin-rename.md` for the complete classified inventory.

## Storage and migration

Source checkouts still default to `<repo>/data`. New installed-user defaults:

| Platform | New default | Recognized legacy source |
| --- | --- | --- |
| Windows desktop | `%LOCALAPPDATA%\FlightMargin` | `%LOCALAPPDATA%\Codex Quota Monitor` |
| Linux installed user | `$XDG_DATA_HOME/flightmargin` or `~/.local/share/flightmargin` | corresponding `codex-quota-monitor` directory |

When the new directory is absent and the recognized legacy directory exists,
FlightMargin copies only `quota.db` and `desktop-preferences.json` through a
staging directory. It never deletes the legacy directory, copies logs/caches,
or overwrites an existing new directory. Explicit data/database overrides are
not migrated. Python and Rust tests cover copy behavior and idempotence.

## Linux LAN binding hardening

On 2026-09-29, the development Linux installer added a dedicated `--lan` mode that binds to `0.0.0.0` instead of embedding a literal DHCP-assigned LAN address in the systemd unit. The secure default remains `127.0.0.1`. The existing `--host ADDRESS` option remains available for advanced/backward-compatible explicit binding and cannot be combined with `--lan`.

The Linux installation and upgrade guidance now uses `--lan`, and regression tests protect the localhost default and wildcard LAN binding contract. This change does not alter the protected production checkout, service, port, database, firewall, authentication state, or network exposure.

## Linux production protection

The existing production deployment remains protected:

- checkout `/opt/codex-quota`;
- service `codex-quota.service`;
- port `8093`;
- database `/opt/codex-quota/data/quota.db`;
- service user, permissions, Codex authentication, credentials, and local data.

On 2026-09-29 the owner explicitly authorized one production configuration
change: a systemd drop-in overrides only `CODEX_QUOTA_HOST` to `0.0.0.0` so
LAN DHCP address changes no longer stop the service. Existing firewall policy
continues to restrict network access to trusted private networks. The protected
production application remains on the legacy 0.2.0 installation; no application
upgrade or data migration accompanied the bind change.

Linux development uses an isolated checkout, ports `18000-18999`, and
temporary service names beginning `codex-quota-test-`.

## Windows beta and packaging

The first public desktop target is Windows 11 x64. WebView2 and an installed,
authenticated Codex CLI are prerequisites. Windows 10 remains unvalidated.

`npm run tauri:build` is the canonical package command and rebuilds the
PyInstaller sidecar before Tauri creates NSIS. The manual GitHub Actions
workflow tests Python/Rust/JavaScript, builds an unsigned installer, and stages:

```text
FlightMargin-0.3.0-beta.1-Windows-x64.exe
FlightMargin-0.3.0-beta.1-Windows-x64.exe.sha256
```

It has read-only contents permission and does not sign, publish, create a tag,
or create a GitHub Release.

Beta 1 relies on the published installer SHA-256 and an independent checksum
match. Unknown Publisher, SmartScreen, and Defender behavior must be recorded.
SignPath is retained as post-beta research and should be reconsidered only when
adoption, user feedback, or concrete warning friction justifies it. No signing
configuration or secrets are required now.

The new bundle identifier intentionally distinguishes FlightMargin from the
internal 0.2.0 application, so an old build may need explicit uninstall and may
temporarily coexist. The user-data copy prevents silent loss of history and
preferences.

## About, privacy, and security

About reports FlightMargin, canonical version, Beta status, detected Codex CLI
version, OS, architecture, and sanitized data/log paths. It states that local
history/preferences/logs are stored locally, the existing authenticated Codex
CLI is used, credentials are not managed or stored, telemetry is absent, the
license is AGPLv3-or-later, and the app is unofficial. Public action links are
available in browser/Linux as normal external links. The Windows shell routes
the same two actions through a Settings-only Tauri command that maps only the
fixed source and issue keys to approved GitHub URLs; it exposes no arbitrary
URL-opening command and does not broaden CSP.

Logs contain concise lifecycle/errors only, rotate at 1 MB, and retain one
prior file. Diagnostics exclude account identity, quota payloads, credentials,
and raw authentication content.

## Feature freeze

Beta 1 adds no multi-provider support, Claude/Gemini/Cursor integrations,
session transcript analytics, token-cost accounting, notifications, mobile
companion, remote monitoring, or auto-update. Those remain possible post-beta
work based on demand. Bug, security, release-blocker, and migration fixes are
allowed.

## Publication preflight (6.20D.3A)

On 2026-09-27, the active Linux development checkout was verified as a fresh
sanitized-history checkout. Strict Git integrity, reachable-history privacy,
focused secret, current-tree, package, CLI, authenticated runtime, browser,
and static systemd checks passed. The old checkout remains archived privately;
it was not accessed as part of this preflight.

The FlightMargin wheel validated as `flightmargin 0.3.0b1` with
`AGPL-3.0-or-later` metadata. Both `flightmargin` and the `codex-quota`
compatibility alias invoke the same implementation. Authenticated collection
confirmed the 5-hour and weekly windows, resets, pace inputs, projected-
exhaustion inputs, credits, and account fields without recording account
values in this document. An isolated loopback dashboard served FlightMargin,
Weekly Pace, Settings, and About successfully.

Generated `flightmargin.service` and legacy-compatible `codex-quota.service`
units passed `systemd-analyze verify`. No temporary system-manager unit was
installed because this preflight is restricted to the development checkout and
does not authorize system-manager changes. The protected production service
was only checked as active and its protected port as listening; no production
files or configuration were accessed or modified.

## Repository publication (6.20D.4)

On 2026-09-27, the repository was renamed to `gmstd66/flightmargin` and made
public after a final tracked-tree privacy sanity check. Its approved description
and topics were applied, and GitHub private vulnerability reporting was enabled.
`main` and `dev/productization` both pointed to the validated Beta 1 code at
publication. History sanitation was completed before publication. No beta tag,
GitHub Release, binary, Sponsor link, or signing submission was created; the
protected production deployment remains unchanged.

## Prior validation baseline

Milestones through integrated commit `381b8e5` established Windows/Linux feature
parity and a lean Windows build. The retained 6.20C baseline measured a
16.835 MiB NSIS installer, 25.464 MiB installed runtime, and no material idle
regression; see `docs/lean-runtime-review.md`. Native Ubuntu validation at
commit `11d94cf` covered authenticated collection, browser/API behavior,
temporary systemd lifecycle, and production isolation.

6.20D.1 must rerun the complete Python suite, locked Cargo check/tests,
JavaScript syntax checks, version/release verification, native Windows NSIS
build, local installer inspection, and `git diff --check`. A native Linux
follow-up is required only for host-specific installer/systemd execution that
cannot be performed from Windows; shared behavior is covered here.

6.20D.1 Windows validation produced a 17,661,083-byte (16.843 MiB) unsigned
NSIS installer, installed FlightMargin beside the internal 0.2.0 build,
verified copy-only migration against an isolated legacy fixture, and confirmed
normal uninstall removes application integration while preserving user data.
The rename added no runtime dependency and increased the installer by only
8,305 bytes (0.047%) from the lean baseline.

## 6.21A local release-candidate validation

The Beta 1 candidate activates Source Code and Report an Issue in About.
Browser/Linux renders two normal external HTTPS links. Windows uses a
Settings-only command whose Rust allowlist accepts only the fixed `source` and
`issues` keys; unit tests reject arbitrary and Sponsor destinations. CSP is
unchanged.

Local Windows validation passed 122 Python tests, JavaScript syntax checks,
canonical/desktop version synchronization, the wheel build and release
verifier, locked Cargo check, 14 Rust tests, and `git diff --check`. The
canonical `npm run tauri:build` rebuilt the PyInstaller sidecar and produced an
unsigned NSIS installer with FlightMargin/`0.3.0-beta.1` metadata. An isolated
direct runtime reached a healthy authenticated Codex collection and exposed
5-hour, Weekly, reset, pace/projection, credits, and history fields without
recording account values. Its sidecar/Codex process tree had no visible console
window, and a second launch exited while the original instance remained.

The local environment has Python 3.14; the GitHub-hosted workflow remains the
required Python 3.12 candidate build. Interactive local UI automation was not
available in the execution session, so About-link clicks and full lifecycle
behavior remain unchecked until validation of the CI installer.

## 6.21A GitHub-hosted candidate evidence

Source `e071c7864fa32ad43fc587dfcf9db354d45b7f42` was identical on `main` and
`dev/productization`. Manual GitHub Actions run `36345996995` succeeded on that
exact SHA. Artifact ID `10941270569`, named
`flightmargin-windows-unsigned-e071c7864fa32ad43fc587dfcf9db354d45b7f42`,
contained exactly the named installer and checksum file. The 17,736,043-byte
installer independently hashed to
`0f8f389784cf99c7ec0946f2629082dc5b8e34ff6e707707a3f8dff615eb09f3`,
matching the checksum file exactly. Metadata reported FlightMargin
`0.3.0-beta.1`; Authenticode reported `NotSigned` with no signer.

Defender antivirus, antispyware, and real-time protection remained enabled and
a custom scan found no threat. An exact-hash test copy with normal Internet-zone
metadata activated SmartScreen and remained behind its prompt; prompt text was
not visible to the noninteractive automation session. The unsigned status is
independently confirmed, so Unknown Publisher behavior remains expected and is
documented for users.

The CI artifact passed isolated install, authenticated Codex discovery and
collection, dashboard/history rendering, About and sanitized diagnostics,
Source/Issue external-browser launch while the FlightMargin webview remained
open, Settings close/reopen, single instance, copy-only internal-0.2.0 data
migration, hidden child-window inspection, preinstall running-app blocking, and
uninstall with user data preserved. The validation used a checkout-local
installation rather than a clean VM. At this stage, visual inspection of the
tray values and manual Retry/Cancel interaction were unavailable; the final
owner acceptance below closes those checks.

The documentation-complete source snapshot
`4f9285f8af7eb78131cd3e1587a8140f43c20ec6` then passed GitHub Actions run
`36348249693`. Artifact ID `10942015033`, named
`flightmargin-windows-unsigned-4f9285f8af7eb78131cd3e1587a8140f43c20ec6`,
contained the same exact two-file installer/checksum set. Its 17,732,166-byte
installer independently hashed to
`98c90184c49be8f5c77625fd960d580cf38c76b3e4d51a03dbce0c3fc1c029a9` and
the checksum matched exactly. FlightMargin `0.3.0-beta.1` metadata,
`NotSigned` status, and a no-threat Microsoft Defender scan were reconfirmed.
This was an intermediate documentation snapshot. The final binary source and
owner acceptance are recorded below.

## 6.21A-F final Beta 1 candidate acceptance

The validated Windows binary was built from
`c9a25dd78e9ab01c5b2ea83abe0c4e923e09111b` by GitHub Actions run
`36356858138`. Artifact
`flightmargin-windows-unsigned-c9a25dd78e9ab01c5b2ea83abe0c4e923e09111b`
contained `FlightMargin-0.3.0-beta.1-Windows-x64.exe` and its checksum file.
The installer's independently verified SHA-256 was
`d742da49292c5166c49f0e5bd0621fae963dbebbd06f4d1a2262b079441bfeec`.
Authenticode reported `NotSigned`.

The exact CI installer passed installation and installed-app smoke validation:
authenticated Codex collection, populated dashboard and History, Settings and
About, both approved external project links, close-to-tray, clean Quit, and no
visible console windows. The owner explicitly reported **PASS** for visual
inspection of the main, Weekly, 5-hour, and Credits tray indicators: they were
present, legible, and matched the dashboard. No private values are recorded.

The owner also reported **PASS** for both running-app installer paths. Cancel
exited without replacing the installed app; FlightMargin remained healthy and
user data stayed intact. For Retry, the owner fully Quit FlightMargin, selected
Retry, observed installation proceed, and confirmed normal relaunch with
authenticated quota collection. Uninstall and user-data/history preservation
also passed owner confirmation.

Defender protection remained enabled and the scan found no threat.
Internet-zone execution invoked SmartScreen; no security control was disabled
or bypassed. The exact warning text is not a gate. This milestone's commit
records acceptance evidence only; it does not change the `c9a25dd` binary
source, build inputs, or artifact, and no rebuild is needed for this record.
The Beta 1 release candidate was validated before publication.

## 6.21B public Beta 1 publication

Annotated tag `v0.3.0-beta.1` resolves to validated binary source commit
`c9a25dd78e9ab01c5b2ea83abe0c4e923e09111b`. GitHub Actions run `36356858138`
built artifact
`flightmargin-windows-unsigned-c9a25dd78e9ab01c5b2ea83abe0c4e923e09111b`.
The public prerelease is
`https://github.com/gmstd66/flightmargin/releases/tag/v0.3.0-beta.1` and exposes
exactly these user assets:

```text
FlightMargin-0.3.0-beta.1-Windows-x64.exe
FlightMargin-0.3.0-beta.1-Windows-x64.exe.sha256
```

The 17,732,301-byte installer is intentionally unsigned and independently
hashed to
`d742da49292c5166c49f0e5bd0621fae963dbebbd06f4d1a2262b079441bfeec`.
An anonymous public download of both assets reproduced that digest and matched
the checksum file exactly. The release is marked prerelease, and its public
page, installation guide, issue tracker, security policy, privacy page, and
repository README all resolved successfully.

This release bookkeeping is documentation-only. It does not change the binary
source, application code, dependencies, build inputs, workflow, or version.
Signing remains deferred. No Sponsor activation, package publication,
auto-update change, or production change occurred.
