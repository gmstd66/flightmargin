# FlightMargin Mobile Relay — Design through I-06A iPhone Foundation

Status: I-05A/I-05B complete; hosted relay live; I-06A native iPhone source and
tests implemented with Mac/Xcode validation pending

## Goal

Provide an iPhone companion path that requires no VPN, port forwarding,
third-party user account, router configuration, or public exposure of the
user's computer.

The desktop/Linux FlightMargin agent sends only normalized quota state to a
central relay. The iPhone retrieves the paired host's latest state through
ordinary HTTPS.

Supabase is the initial relay implementation, not part of the public client
contract. A future backend can replace it without changing the FlightMargin
credential or JSON contract.

## Trust boundaries

```text
Codex CLI
   |
   v
FlightMargin desktop/Linux agent
   |  HTTPS + host credential
   v
Supabase Edge Function
   |  privileged server-side database access
   v
Postgres relay tables
   ^
   |  HTTPS + device credential
   |
FlightMargin iPhone
```

Rules:

- OpenAI/Codex credentials never leave the host.
- Prompts, transcripts, source code, agent output, and local history never
  enter the relay.
- Clients do not receive a Supabase secret key, service-role key, database
  password, or direct table access.
- FlightMargin credentials are unique per host/device and independently
  revocable.
- Long-lived credential secrets are generated locally by the client and stored
  only in the platform's secure local storage.
- The relay stores only keyed HMAC-SHA-256 digests of long-lived credentials.
- The HMAC pepper lives only in the Edge Function secret store.
- The public registration endpoint is protected by server-side rate limits.
  Because FlightMargin is open source, a client-embedded registration secret is
  not considered a meaningful security boundary.

## Supabase access model

Relay tables live in the `public` schema for simple server-side access, but:

1. Row Level Security is enabled on every relay table.
2. All table privileges are revoked from `anon` and `authenticated`.
3. No client RLS policies are created.
4. Only the server-side `service_role` path may read/write relay tables.
5. Desktop and iPhone clients call the Edge Function only.

This deliberately avoids coupling FlightMargin's product identity to Supabase
Auth. Users do not create a FlightMargin or Supabase account for v1.

## Credential format

Host credential:

```text
fmh1.<credential-uuid>.<base64url-32-byte-secret>
```

Device credential:

```text
fmd1.<credential-uuid>.<base64url-32-byte-secret>
```

Pairing QR credential:

```text
fmp1.<pairing-session-uuid>.<base64url-32-byte-secret>
```

Manual pairing code:

```text
ABCDE-FGHIJ
```

The manual code uses 10 Crockford-Base32 characters (about 50 bits), expires
after five minutes, and is limited to five failed attempts per pairing session.

The Edge Function hashes credentials contextually:

```text
HMAC-SHA256(
  relay_pepper,
  credential_kind + ":" + credential_id + ":" + secret
)
```

The database stores the 64-character hexadecimal digest, never the raw secret.
Pairing material uses separate `pairing-qr:<session-id>:<secret>` and
`pairing-manual:<unhyphenated-code>` HMAC contexts so its digests cannot be
reused as host or device credential digests.

## Local credential storage

- iOS: Keychain.
- Windows: the host credential is encrypted for the current user with native
  Windows DPAPI and the protected blob is stored in
  `mobile-relay-host.json` under the FlightMargin application-data directory.
- Linux: owner-only credential file (`0600`) under the FlightMargin data
  directory until a portable keyring strategy is adopted.

I-05A creates the host UUID, credential UUID, and 32-byte random secret once,
only after the user enables Mobile Relay. It reuses that identity across
restarts and transient registration failures. A malformed identity file fails
closed and is not silently replaced. On Linux the containing directory is
created with `0700` where FlightMargin creates it; the identity file is always
written with `0600`. On Windows plaintext is passed to DPAPI only in process
and is never written to disk. The host token is independent of Codex/OpenAI
authentication and can be revoked independently at the relay. Disabling relay
sync preserves the identity and all local quota/history data; reset/revocation
UI remains deferred.

## I-05A host integration

The packaged application contains four separated responsibilities under
`app/mobile_relay/`:

- `config.py`: persistent opt-in state and strict endpoint validation;
- `identity.py`: stable host identity and DPAPI/Linux secret storage;
- `client.py`: bounded standard-library HTTP/TLS transport with redirects
  rejected;
- `sync.py`: registration, latest-only uploads, pairing, and retry state.

Relay support defaults off. The normal endpoint is
`https://samcdyrwfwrlxzypzgmj.supabase.co/functions/v1/relay-v1`. Developers
may set `FLIGHTMARGIN_RELAY_ENDPOINT` before application startup; HTTPS is
required except for loopback HTTP (`localhost`, `127.0.0.0/8`, or `::1`). The
dashboard API accepts only an `enabled` boolean and cannot change the endpoint.
HTTPS uses the platform trust store with certificate verification, timeouts are
bounded at five seconds, and redirects are rejected rather than following an
untrusted destination.

After each successful local collector result, the coordinator retains one
in-memory latest sample. It registers the stable identity idempotently, then
uploads only that sample. It never queues history and never changes local
collection or SQLite behavior. Duplicate notification of the same SQLite
sample ID/timestamp does not trigger a second upload, and one operation lock
prevents concurrent upload/pairing transport. Failures do not propagate into
the collector or dashboard. Retry delays step through 2, 5, 15, 30, 60, and
300 seconds, remain capped at five minutes, and reset after success.

The host upload serializer has an explicit allowlist and emits exactly:

```text
schema_version, sampled_at,
five_hour_used, five_hour_reset_at,
weekly_used, weekly_reset_at,
plan_type, reset_credits_available, credits_balance,
spend_control_reached, rate_limit_reached_type,
collector_state, collector_message_code
```

It cannot serialize database IDs, local paths, usernames, history, Codex
credentials, prompts, transcripts, source, or agent output. The host credential
is used only in registration JSON or the Authorization header and is never
returned by the dashboard API, placed in a URL, or logged.

Settings now has a **Mobile Relay** tab showing Disabled, Registering,
Connected, or Offline / Retry scheduled plus the last successful upload.
Pairing is available only when connected and only after an explicit button
press. The returned manual code, expiry countdown, and QR encoding the returned
deep link remain in browser memory and DOM only until expiry, disablement, or
replacement. QRCode.js is packaged locally; no CDN request is made. Pairing
material is never stored in SQLite or the relay settings/identity files. The UI
does not claim that a mobile application is currently available.

## Host registration

Registration is accountless. The host generates locally:

- host UUID;
- host credential UUID;
- 32 random credential bytes;
- display name, platform, and app version.

```http
POST /v1/hosts/register
Content-Type: application/json
```

```json
{
  "host_id": "uuid",
  "display_name": "COXON",
  "platform": "linux",
  "app_version": "0.3.0-beta.1",
  "credential": "fmh1.<uuid>.<secret>"
}
```

The Edge Function validates the token shape, HMACs the secret, inserts the host
and credential, and discards the raw credential. Registration is idempotent
when the same host ID, credential ID, and credential secret are retried.
Retrying with that same identity does not update the host metadata established
by the first successful registration.

```json
{
  "api_version": 1,
  "host_id": "uuid",
  "registered": true,
  "result": "registered"
}
```

An idempotent retry returns `registered: false` and
`result: "already_registered"`.

## Quota report

Authenticated with the host credential:

```http
PUT /v1/quota
Authorization: Bearer fmh1.<credential-uuid>.<secret>
Content-Type: application/json
```

Payload version 1 mirrors FlightMargin's normalized Codex quota fields rather
than derived UI metrics:

```json
{
  "schema_version": 1,
  "sampled_at": "2026-09-29T17:00:00Z",
  "five_hour_used": 42.5,
  "five_hour_reset_at": "2026-09-29T19:12:00Z",
  "weekly_used": 78.0,
  "weekly_reset_at": "2026-10-02T15:00:00Z",
  "plan_type": "plus",
  "reset_credits_available": 3,
  "credits_balance": 12.5,
  "spend_control_reached": false,
  "rate_limit_reached_type": null,
  "collector_state": "ok",
  "collector_message_code": null
}
```

All quota values may be null when Codex does not supply that field. Percentage
values, when present, must be between 0 and 100.

The relay updates one current-state row per host. Reports older than the stored
`sampled_at` are ignored so delayed requests cannot move state backward.
Each accepted report also updates the host's `last_seen_at`.

No remote history is stored in I-01.

## Pairing

### Start pairing

Host-authenticated request:

```http
POST /v1/pairings
Authorization: Bearer fmh1.<credential-uuid>.<secret>
```

The relay generates a UUID, a cryptographically random 32-byte QR secret, and
a 10-character uppercase Crockford Base32 manual code. The response is:

```json
{
  "api_version": 1,
  "pairing_token": "fmp1.<session-uuid>.<base64url-secret>",
  "manual_code": "ABCDE-FGHIJ",
  "expires_at": "2026-09-29T17:05:00Z",
  "deep_link": "flightmargin://pair/v1?token=fmp1.<session-uuid>.<base64url-secret>"
}
```

The relay stores only contextual HMAC-SHA-256 digests. The expiration is
exactly five minutes after the database creation timestamp, and every session
starts with zero attempts and a maximum of five. Manual-code collisions are
prevented under a transaction-scoped advisory lock and regenerated.

QR payload:

```text
flightmargin://pair/v1?token=fmp1.<session-uuid>.<secret>
```

### Claim pairing

The iPhone generates its own device UUID and device credential before
submitting the claim.

```http
POST /v1/pairings/claim
Content-Type: application/json
```

```json
{
  "pairing_token": "fmp1.<session-uuid>.<secret>",
  "device_id": "uuid",
  "display_name": "iPhone",
  "platform": "ios",
  "credential": "fmd1.<uuid>.<secret>"
}
```

Manual-code claim uses `manual_code` instead of `pairing_token`.

Exactly one pairing method is required. Pairing tokens and manual codes must
use their canonical forms; manual input is uppercase `XXXXX-XXXXX` and uses
the Crockford alphabet without `I`, `L`, `O`, or `U`. Device UUID, credential,
display name, and platform are strictly validated and bounded.

A successful claim locks the pairing and host rows, verifies the digest in
Python with `hmac.compare_digest`, creates one device and one credential row,
stores only the contextual device-credential HMAC digest, and marks the
session claimed in the same transaction. Advisory locks also serialize reuse
of device and credential UUIDs across different sessions. The same active
device with the same credential may retry an already-completed claim after a
lost response; a different device or credential cannot reclaim it. A newly
paired device can immediately authenticate to `GET /v1/quota`.

An incorrect secret for a valid QR session increments `attempts` atomically;
the fifth mismatch exhausts the session permanently. Because a manual code
does not carry a session identifier, a code whose digest matches no row cannot
be attributed to a particular session and therefore cannot increment that
session. It is still rejected with the same response as every other claim
failure. Deployment must apply the planned per-IP claim rate limit in addition
to the 50-bit manual-code entropy.

Malformed public input returns `422`. Unknown, incorrect, expired, exhausted,
host-revoked, or already-claimed-for-another-device claims all return `400`
with `Pairing could not be completed`; this prevents the API response from
confirming whether a well-formed manual code exists. Missing or invalid host
authentication on pairing creation retains the I-02 `401` behavior.

## iPhone quota read

```http
GET /v1/quota
Authorization: Bearer fmd1.<credential-uuid>.<secret>
```

The response includes the paired host metadata, latest raw quota snapshot,
`sampled_at`, `received_at`, and `last_seen_at`. The iPhone computes
time-dependent remaining/reset/pace/stale presentation locally.

The I-02 response shape is:

```json
{
  "api_version": 1,
  "host": {
    "id": "uuid",
    "display_name": "COXON",
    "platform": "linux",
    "app_version": "0.3.0-beta.1",
    "last_seen_at": "2026-09-29T17:01:00Z"
  },
  "quota": {
    "schema_version": 1,
    "sampled_at": "2026-09-29T17:00:00Z",
    "received_at": "2026-09-29T17:00:01Z",
    "five_hour_used": 42.5,
    "five_hour_reset_at": "2026-09-29T19:12:00Z",
    "weekly_used": 78.0,
    "weekly_reset_at": "2026-10-02T15:00:00Z",
    "plan_type": "plus",
    "reset_credits_available": 3,
    "credits_balance": 12.5,
    "spend_control_reached": false,
    "rate_limit_reached_type": null,
    "collector_state": "ok",
    "collector_message_code": null
  }
}
```

`quota` is `null` until the paired host submits its first report.

## Device management

Reserved host-authenticated endpoints:

```text
GET    /v1/devices
DELETE /v1/devices/<device-id>
```

Revocation sets `revoked_at`; a revoked credential immediately loses access.

## I-06A native iPhone client

The repository now contains an iOS 17 SwiftUI client under `ios/`. It uses
URLSession and Codable directly against the provider-independent v1 API; it
does not embed a Supabase SDK or any third-party runtime package. The app
accepts canonical `flightmargin://pair/v1` links and normalized Crockford
manual codes. Before its first claim attempt it commits a stable device UUID
and `fmd1` credential to a non-synchronizing ThisDeviceOnly Keychain item so a
lost response can be retried with the exact same identity.

Only the Keychain stores the device credential. UserDefaults may hold the
paired host UUID, cached quota envelope, and last successful app refresh.
Foreground quota reads are serialized, repeat approximately every 60 seconds,
pause in the background, and preserve cached quota on failure. Reset removes
all of that local state, but relay v1 currently has no device-side remote
revocation endpoint; the UI says so explicitly.

This source milestone does not claim native compilation from Linux. Xcode,
XCTest, Simulator, Keychain, cold/warm URL, and later physical-iPhone testing
are documented in `docs/ios-development.md`. The relay v1 contract and backend
are unchanged.

## Edge Function layout

The hosted implementation is one Supabase Edge Function named `relay-v1` under
`supabase/functions/relay-v1/`, with internal routing for `/health` and the v1
contract. `supabase/config.toml` sets `verify_jwt = false`: the function uses
FlightMargin `fmh1` and `fmd1` credentials rather than Supabase Auth accounts
or Supabase JWTs. Every protected route authenticates the FlightMargin token
before application data access.

The function uses a module-scope `node-postgres` pool with at most one
connection per warm isolate, no named/prepared statements, bounded
connection/query behavior, and TLS certificate verification for hosted
connections. It reads only `FLIGHTMARGIN_RELAY_DATABASE_URL`. Hosted
deployment must set that secret to the Supabase shared transaction-pooler URL
on port 6543 with the custom-role username
`flightmargin_relay.<SUPABASE_PROJECT_REF>`; local tests set it to the local
PostgreSQL URL. There is no fallback to the built-in direct `SUPABASE_DB_URL`.
All SQL values are
parameterized. Explicit `BEGIN`/`COMMIT`/`ROLLBACK`, transactional row locks,
and advisory transaction locks preserve the registration, authentication,
monotonic quota, and pairing concurrency semantics established by the Python
reference.

Public JSON endpoints require `application/json`, accept at most 16 KiB, and
enforce the same field/type/length constraints as the Python implementation.
Routes and methods are explicit, CORS is not enabled, internal failures return
a generic response, and the only logged failure attribute is a safe request
ID. FlightMargin application code does not persist or log raw client IPs,
authorization values, bodies, pairing material, or credentials. Supabase
infrastructure and its gateway may retain request metadata, including
client-IP-related headers, according to Supabase platform logging and
retention; FlightMargin does not control those infrastructure logs.

## Database tables

I-01 defines:

- `relay_hosts`
- `relay_host_credentials`
- `relay_devices`
- `relay_device_credentials`
- `relay_pairing_sessions`
- `relay_quota_state`

See `supabase/migrations/20260929173100_mobile_relay.sql`.

I-04B adds the dedicated `flightmargin_relay` PostgreSQL login role. It cannot
inherit privileges, bypass RLS, create roles or databases, replicate, or act as
a superuser. It has schema `USAGE` but not `CREATE`; it can select, insert, and
update the seven relay tables, and can delete only from
`relay_rate_limit_buckets`. Explicit role-specific RLS policies match that
table privilege surface. The migration contains no password. The role password
is a hosted operational secret configured outside Git and used only in the
`FLIGHTMARGIN_RELAY_DATABASE_URL` function secret.

## Development and backup model

Relay development is local-first. The canonical schema, Edge Function source,
tests, seed data, and configuration live in the FlightMargin Git repository.
Developers run Supabase locally on COXON (or another development machine), test
migrations/functions there, commit them to the active development branch, and
push to GitHub before deploying the same committed revision to the hosted
Supabase project.

The local development database and the hosted relay database have different
roles:

- local development database: disposable and reproducible from Git migrations
  plus development seed data;
- hosted Supabase database: operational relay state;
- COXON backup archive: scheduled logical copies of hosted relay data for
  disaster recovery.

Hosted production/staging data is never used as the normal development
database. Backups are not committed to Git and must be stored outside the
repository with restricted filesystem permissions.

See `docs/mobile-relay-development.md`.

## Retention

- latest quota state: one row per registered host;
- pairing sessions: purge after 24 hours;
- revoked credentials/devices: retain temporarily for audit/debugging;
- no remote quota history in v1.

## I-04A public rate limits

The public Edge Function enforces database-backed fixed-window limits before
processing unauthenticated request bodies:

- host registration: 10 requests per IP identity per 60 minutes;
- pairing claim: 20 requests per IP identity per 5 minutes, in addition to the
  five failures permitted for a session-addressable QR claim.

The identity is selected from `cf-connecting-ip`, then `x-real-ip`, with one
shared `unknown` identity when neither is present. Only
`HMAC-SHA-256(pepper, "rate-limit-ip:" + identity)` is stored. Atomic
PostgreSQL upserts increment fixed-window buckets, and over-limit responses are
generic `429` responses with `Retry-After`. An expiry index supports periodic
purging; the implementation also removes expired buckets during checks. The
`relay_rate_limit_buckets` stores only these contextual HMAC digests, not raw
client IPs. FlightMargin application code does not persist or log raw client
IPs. Supabase infrastructure and its gateway may retain request metadata,
including client-IP-related headers, according to Supabase platform logging
and retention; FlightMargin does not control those infrastructure logs.

## Deferred work

Not part of I-01:

- Apple Push Notification service integration;
- remote quota history;
- multiple-host iPhone UI;
- end-to-end encryption of the quota payload;
- optional FlightMargin user accounts;
- web dashboard;
- billing/subscription logic;
- production-grade abuse scoring.

## Implementations through I-05

The first working relay API is separate source under `relay/`; it is excluded
from normal FlightMargin package discovery and runs from a source checkout
with `python -m relay`. It does not share routes, configuration, storage, or
process lifecycle with the browser/dashboard API under `app/`. It implements
`GET /health`, accountless
`POST /v1/hosts/register`, host-authenticated `PUT /v1/quota`, and
device-authenticated `GET /v1/quota` against the I-01 PostgreSQL schema.

The process reads only `FLIGHTMARGIN_RELAY_DATABASE_URL` and
`FLIGHTMARGIN_RELAY_PEPPER`; the pepper must encode to at least 32 bytes.
Runtime PostgreSQL connections use a five-second connection timeout, and
credential digests are checked in process with constant-time comparison after
credential-ID lookup. I-03 adds host-authenticated pairing creation and
accountless device claim using the existing I-01 tables and without a schema
change. Local development startup is intentionally fixed to
`127.0.0.1:18093`. `/health` is process liveness only and does not imply
PostgreSQL readiness. QR rendering, iPhone UI, rate limiting, hosted Supabase
deployment, device-management endpoints, and production operations remain
outside I-03.

I-04A adds the production-oriented TypeScript/Deno implementation under
`supabase/functions/relay-v1/`. It preserves the same JSON/status behavior and
credential/HMAC contexts, and adds the public-edge controls and database-backed
limits required before exposure. The Python implementation remains the local
reference and is not replaced or packaged with the main FlightMargin app.

The manual-only GitHub workflow `.github/workflows/deploy-mobile-relay.yml`
defines an explicit two-phase hosted path. `phase=prepare` checks out the exact
selected commit, links the hosted project with the administrative database
password, and runs committed migrations only. `phase=deploy` checks out the
exact selected commit, validates and installs the HMAC pepper and shared
transaction-pooler URL, and deploys `relay-v1`; it cannot access the
administrative database password or run `supabase db push`. The URL validator
requires username `flightmargin_relay.<SUPABASE_PROJECT_REF>`, a
`*.pooler.supabase.com` host, port `6543`, and a password. I-04A/I-04B do not
run the workflow, create its secrets, link a hosted project, or deploy
anything.

The exact first-deployment sequence is: (1) push the reviewed revision; (2)
manually run `phase=prepare` on that exact revision; (3) let migrations create
`flightmargin_relay`; (4) set its strong password outside Git/CI; (5) construct
the transaction-pooler URL in the form
`flightmargin_relay.<PROJECT_REF>@*.pooler.supabase.com:6543`; (6) save the
complete URL as `FLIGHTMARGIN_RELAY_DATABASE_URL`; (7) configure
`FLIGHTMARGIN_RELAY_PEPPER`; (8) manually run `phase=deploy` on the **same
revision**; and (9) perform hosted smoke tests. Later releases normally run
only `phase=deploy`, unless new migrations first require `phase=prepare`.

The credential and pairing design leaves room for adding payload encryption
later without changing device identity.

I-05A adds the optional packaged host client described above without bundling
the local Python relay server or adding a Python runtime dependency. Relay is
opt-in and disabled by default. Local validation uses the Python reference at
`127.0.0.1:18093` and disposable PostgreSQL at `127.0.0.1:55432`; completed
I-05B validation additionally proves the Linux host against the live hosted
relay, the public registration/claim thresholds and scoped bucket cleanup, and
the native Windows DPAPI, wheel, PyInstaller, Tauri, NSIS, and packaged-sidecar
path.

I-06A now provides native iPhone source and tests. Native Mac validation and
I-06B real QR/manual physical-iPhone pairing remain, and are not unfinished
I-05 host-validation items. The client consumes the validated pairing/quota v1
API without changing the backend contract. The protected `/opt/codex-quota`
production installation is unchanged, and published `v0.3.0-beta.1` remains
immutable.
