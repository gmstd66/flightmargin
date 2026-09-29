# FlightMargin Mobile Relay — Design and I-02 Local API

Status: approved architecture, local I-02 implementation; not deployed

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

## Local credential storage

- iOS: Keychain.
- Windows: Windows Credential Manager/DPAPI-backed storage.
- Linux: owner-only credential file (`0600`) under the FlightMargin data
  directory until a portable keyring strategy is adopted.

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

The desktop generates a session UUID, high-entropy QR secret, and manual code.
The relay stores only their HMAC digests and a five-minute expiration.

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

A successful claim atomically verifies expiry/attempts, creates the device,
stores its credential digest, and marks the session claimed. The same
device/credential may retry an already-completed claim after a lost response;
a different device cannot claim the same session.

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

## Edge Function layout

Initial deployment uses one Edge Function named `flightmargin-relay` with
internal routing for `/v1/*`.

The function uses FlightMargin credentials rather than Supabase user JWTs.
Every protected route authenticates the FlightMargin token before database
access.

## Database tables

I-01 defines:

- `relay_hosts`
- `relay_host_credentials`
- `relay_devices`
- `relay_device_credentials`
- `relay_pairing_sessions`
- `relay_quota_state`

See `supabase/migrations/20260929173100_mobile_relay.sql`.

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

## Initial rate-limit targets

- host registration: 5/hour/IP;
- pairing claim: 20/hour/IP and maximum 5 failures/session;
- quota report: 30/minute/host credential;
- quota read: 120/minute/device credential.

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

## I-02 local implementation

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
credential-ID lookup. Local development startup is intentionally fixed to
`127.0.0.1:18093`. `/health` is process liveness only and does not imply
PostgreSQL readiness. Pairing, rate limiting, hosted Supabase deployment,
device-management endpoints, and production operations remain outside I-02.

The credential and pairing design leaves room for adding payload encryption
later without changing device identity.
