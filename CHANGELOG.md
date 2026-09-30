# Changelog

Notable changes to FlightMargin are documented here. This file summarizes product-facing history; Git retains the detailed engineering history.

## Unreleased

### Added

- Added the manual-only I-05B validation workflow for independent hosted
  public-rate-limit checks and native Windows DPAPI/package checks. Hosted
  cleanup snapshots complete rate-bucket primary keys and deletes only newly
  created keys; Windows uses the locked canonical Tauri/PyInstaller build,
  an explicit application/desktop/mobile-host Python test scope, cross-process
  real DPAPI checks, wheel asset verification, and an isolated packaged-sidecar
  smoke. It does not deploy, migrate, publish, upload, or run automatically.
  Hosted rate-limit validation passed in run `36783584246`; native Windows
  DPAPI and package evidence remain pending a rerun after correcting the test
  scope exposed by that run.
- Added I-05A opt-in desktop/Linux Mobile Relay integration. FlightMargin now
  creates a stable dedicated host identity, uses Windows DPAPI or an owner-only
  Linux credential file, registers idempotently, uploads only the latest exact
  normalized v1 quota payload, and retries failures with bounded backoff while
  local collection/history remain unaffected. Relay remains off by default.
- Added a Mobile Relay Settings tab with Disabled/Registering/Connected/Offline
  status, last successful sync, and explicit five-minute mobile pairing. The
  manual code and locally generated QR presentation are cleared after expiry
  and are never persisted; packaged QRCode.js avoids a CDN/runtime dependency.
- Added I-04B pre-deployment database hardening with a dedicated non-elevated
  `flightmargin_relay` login, exact relay-table grants, and matching explicit
  RLS policies. The role can delete only rate-limit buckets; its operational
  password is intentionally absent from Git and migrations.
- Added the I-04A production-oriented TypeScript/Deno Supabase Edge Function
  for the complete relay v1 contract, with direct transactional PostgreSQL
  access, FlightMargin-native authentication, strict public request handling,
  shared Python/TypeScript HMAC vectors, and standalone Deno integration tests.
- Added database-backed fixed-window public limits of 10 host registrations per
  IP-HMAC per hour and 20 pairing claims per IP-HMAC per five minutes. A new
  additive migration stores no raw IPs and supports expired-bucket purging.
- Added a manual-only GitHub-hosted deployment workflow that will apply
  committed migrations in an explicit `prepare` phase, then configure the
  server-only pepper and explicit shared transaction-pooler URL and deploy the
  exact same selected `relay-v1` revision in a separate `deploy` phase. The
  runtime phase has no administrative database credential or migration path.
  I-04A/I-04B perform no hosted deployment.
- Added the I-03 accountless mobile pairing API with host-authenticated
  five-minute pairing creation, QR token/manual code/deep-link responses,
  atomic QR and manual claims, five-attempt session exhaustion, idempotent
  lost-response retries, concurrent-claim protection, and immediate use of
  newly issued device credentials. Pairing and device secrets are represented
  in PostgreSQL only by context-separated HMAC-SHA-256 digests; the existing
  I-01 schema required no migration.
- Added the first working local mobile relay API as isolated reference source:
  accountless idempotent host registration, contextual HMAC-SHA-256 host and
  device authentication, monotonic latest-quota updates, and paired-device
  quota reads backed by the existing protected PostgreSQL schema. Integration
  tests use the disposable local database and the manual server binds only to
  `127.0.0.1:18093`; pairing and hosted deployment remain deferred.
- Defined the accountless mobile-relay architecture for the iPhone companion,
  including revocable host/device credentials, five-minute QR/manual pairing,
  a provider-independent v1 quota API, and the initial Supabase schema with
  RLS plus revoked direct client grants. Relay development is local-first with
  Git as the schema/code source of truth, and hosted relay data will have an
  independent scheduled backup archive on COXON. No relay project or production
  backend is deployed by this milestone.

### Fixed

- Scoped the Linux host-identity exact-`0600` permission assertion to Linux,
  where POSIX mode bits are meaningful, so Windows validation can continue to
  the separate native DPAPI and package checks without weakening Linux
  credential-file coverage.
- Prevented Python and Deno relay database integration tests from inheriting a
  hosted database target from normal runtime configuration. Automated tests now
  accept only syntactically loopback PostgreSQL URLs through dedicated test
  variables, with a loopback-only runtime-variable fallback for existing local
  development workflows.
- Strengthened the manual relay deployment check to require the
  `flightmargin_relay.<SUPABASE_PROJECT_REF>` custom-role username, a Supabase
  shared-pooler host, and port 6543 before installing the runtime database URL
  as a function secret.
- Hardened I-04A hosted database access by replacing pipelining Postgres.js
  with a one-client `node-postgres` pool, explicit transactions, unnamed
  parameterized queries, verified hosted TLS, and the required
  `FLIGHTMARGIN_RELAY_DATABASE_URL` transaction-pooler secret. Clarified that
  FlightMargin code stores only contextual IP HMACs and does not log raw client
  IPs, while Supabase infrastructure may retain request metadata under its own
  logging and retention.
- Hardened the local mobile relay before push with explicit v1 response
  envelopes, immutable host metadata on registration retries, bounded strict
  request validation, a minimum 32-byte HMAC pepper, constant-time credential
  digest checks, five-second PostgreSQL connection timeouts, and exclusion of
  the reference relay source from normal FlightMargin package discovery.
- Hardened Linux LAN deployment with a dedicated `--lan` installer mode that binds to `0.0.0.0` instead of a single DHCP-assigned address, so the service continues to start after LAN IP changes. Localhost remains the secure default, and explicit `--host ADDRESS` binding remains available for advanced deployments.

## 0.3.0-beta.1 - 2026-09-27

### Added

- Published the first FlightMargin public beta as a GitHub prerelease with the
  validated unsigned Windows 11 x64 installer and its SHA-256 checksum. Tag
  `v0.3.0-beta.1` points to binary source commit
  `c9a25dd78e9ab01c5b2ea83abe0c4e923e09111b`.
- Activated About actions for the public source repository and issue tracker
  in browser/Linux use and through an exact allowlisted external-browser bridge
  in the Windows desktop shell.
- Added the first-public-beta release-notes draft and explicit Windows
  checksum-verification guidance for the intentionally unsigned installer.
- Validated the unsigned Beta 1 candidate through the GitHub-hosted Windows
  workflow, independent SHA-256 verification, Defender scanning, and isolated
  installed-application checks. The owner accepted the tray indicators, both
  running-app installer paths, and uninstall/data preservation. Later
  acceptance and release bookkeeping commits contain documentation only; the
  published binary source remains `c9a25dd78e9ab01c5b2ea83abe0c4e923e09111b`.
- Published the FlightMargin source repository as
  `https://github.com/gmstd66/flightmargin` after the sanitized-history and
  final privacy checks. Applied the approved description/topics and enabled
  GitHub private vulnerability reporting. No beta tag, GitHub Release, binary,
  signing submission, or production change was made.
- Completed the Linux publication preflight against the sanitized development
  checkout: history/current-tree privacy and secret scans, wheel and CLI
  verification, authenticated local runtime and browser validation, static
  FlightMargin/legacy systemd checks, and production-isolation checks. The
  repository remained private at that preflight point; no release or production
  change was made.
- Added a reviewable pre-public Git-history sanitation plan covering the
  private backup, full-history privacy/secret inventory, exact rewrite and
  leased-push strategy, GitHub residual exposure, and post-rewrite validation.
- Created and fully validated a sanitized-history candidate with an unchanged
  current HEAD tree, preserved topology and dates, approved noreply metadata,
  and clean privacy, secret, and integrity scans.
- Installed the exact validated `main`, `dev/productization`, and annotated
  baseline-tag histories on the private GitHub repository in one atomic update
  guarded by explicit old-ref leases, then verified them from a fresh clone.
- Adopted the FlightMargin public identity across the Windows application,
  NSIS metadata, browser dashboard, Linux CLI/service defaults, packaging,
  release artifacts, About content, and current documentation.
- Added copy-only, idempotent migration of legacy Windows/Linux history and
  preferences into FlightMargin data directories while preserving legacy data.
- Added the standard GNU Affero General Public License v3 text and
  `AGPL-3.0-or-later` package metadata.
- Added the canonical `flightmargin` CLI while retaining `codex-quota` as a
  beta compatibility alias.

- Project continuity and milestone-handoff documentation.
- Reproducible local wheel build, artifact verification, and isolated installed-wheel release check scripts.
- Docker deployment feasibility findings and authentication-model investigation.
- Native desktop architecture feasibility findings and a Windows-first implementation proposal.
- Windows-first desktop prototype: Tauri 2 shell scaffold, PyInstaller sidecar build, loopback readiness protocol, desktop data paths, and cross-platform Codex discovery.
- Native Windows internal validation for the Tauri/PyInstaller desktop prototype, including unsigned MSI and NSIS artifacts, installed-app startup, host Codex discovery, authenticated quota collection, and app-data persistence.
- Windows beta desktop lifecycle: tray controls, single-instance activation, opt-in start-at-login, bounded local shell logs, and a repeatable Windows beta checklist.
- Owner GUI/product review walkthrough for the internal Windows desktop build.
- Compact configurable Windows dashboard with persisted panel visibility and quota-state colors.
- Native Settings About tab with canonical version, local-data privacy notes,
  Codex CLI detection, attribution, and sanitized copyable diagnostics.
- Windows public-beta preparation: manual GitHub-hosted candidate workflow,
  checksummed unsigned NSIS artifacts, resolved dependency inputs, public user
  and contributor documentation, signing/versioning plans, and release gates.
- Linux/browser platform-parity matrix and browser-accessible Settings/About
  behavior using the same local preference and diagnostic APIs as Windows.
- Native Linux runtime validation for platform parity: isolated authenticated
  collection, browser/API and unavailable-Codex checks, temporary systemd
  lifecycle, resource baseline, and production-isolation verification.

### Changed

- Validated the first GitHub-hosted unsigned Windows candidate, its independent
  checksum, Defender result, SmartScreen activation, isolated install/runtime,
  migration, external project links, and uninstall/data-preservation behavior.
- Made the owner-approved Beta 1 policy explicit: the installer is intentionally
  unsigned, SHA-256 verification is required, SmartScreen/Unknown Publisher and
  Defender observations must be recorded, and SignPath is deferred until user
  adoption or feedback justifies reconsideration.
- Advanced the single canonical version to `0.3.0-beta.1` and synchronized
  generated Tauri/Cargo metadata and release validation.
- Froze the Beta 1 feature set; only bug, security, release-blocker, and
  migration fixes remain in scope before publication review.

- Completed the measurement-driven lean runtime review: reduced the Windows
  installer by 9.2%, reduced app-owned steady RSS by 21.3% for the measured npm
  Codex installation, removed a duplicate startup quota sample, and retained
  existing Windows/Linux functionality and polling freshness.
- Windows release builds now exclude optional Setuptools/PyYAML sidecar weight,
  use safe Cargo LTO/strip settings, resolve recognized official npm shims to
  native Codex with a compatibility fallback, and reliably run the canonical
  sidecar-rebuilding `npm run tauri:build` flow.
- Recorded the planned free, open-source distribution model: voluntary GitHub Sponsors support, GitHub Releases for future public installers, and a preference for qualifying free open-source code signing.
- Fixed Windows sidecar startup by passing the pre-bound loopback socket directly to Uvicorn.
- Added Windows Tauri icon configuration, current shell-plugin compatibility, clear sidecar-startup and collector diagnostics, and process-tree shutdown for PyInstaller one-file sidecars.
- Selected a current-user NSIS installer as the internal beta path and preserved per-user SQLite data on normal uninstall and upgrade.
- Standardized the dashboard title on Codex Quota Monitor and made collector status updates accessible to screen readers.
- Simplified the owner-reviewed Windows dashboard to a fixed compact responsive layout with visibility-only customization. Drag/reorder, arbitrary resizing, persisted geometry, and obsolete Settings controls were removed; schema 4 resets incompatible layout geometry while preserving unrelated preferences.
- Restored the Weekly History graph immediately when a hidden panel is shown and accepted decimal sidecar percentages when updating the numeric Windows tray indicators.
- Opened Settings in a focused, DPI-aware native window beside the dashboard and added Windows hidden-icons guidance for quota indicators.
- Removed the legacy in-dashboard Settings fallback in favor of a dedicated native-window page, and tightened three-digit tray rendering so `100` remains fully visible.
- Added a green purchased-Credits tray indicator using floored whole balances, a `999+` overflow glyph, exact-value tooltips, and the existing tray preference and collector stream.
- Restored resilient tray startup by creating unknown-state informational icons immediately, accepting both two-field and three-field sidecar samples, retaining the normal tray handle directly, and logging each icon failure independently.
- Granted the native Settings commands through narrow Tauri 2 capabilities and
  added tray **Settings...** and **About...** actions that reuse the adjacent
  singleton Settings window.
- Reduced compact Weekly History Y-axis labels to 8 px while retaining all five
  percentage ticks and the existing X-axis sizing.
- Expanded Weekly History and its chart through a bounded viewport-height chain
  instead of leaving unused space below a fixed shallow card. Windows Tauri
  release builds now rebuild the PyInstaller sidecar first so current embedded
  dashboard assets cannot be replaced by a stale sidecar executable.
- Hardened NSIS upgrades by detecting a still-running packaged backend and
  asking the user to Quit from the tray and Retry before files are copied.
- Removed machine-specific private deployment details from the current public
  documentation while recording remaining Git-history privacy decisions.
- Consolidated normal/warning/critical quota state in the shared Python API,
  aligned unavailable and zero-credit display behavior, made narrow browser
  layouts reflow without clipping, and kept Windows-only startup/tray controls
  out of the Linux browser surface.
- Recorded the owner selection of AGPLv3-or-later; the license was subsequently
  applied in the FlightMargin public identity milestone.
- Fixed Windows-formatted About paths to retain backslash separators when
  platform diagnostics are generated on a non-Windows host.

- Made `app.version.__version__` the canonical application version used by setuptools metadata, the CLI, API responses, and Codex app-server client identification.

## 0.2.0

### Added

- Local-first browser dashboard for 5-hour and weekly Codex quota monitoring, reset timing, sustainable pace, exhaustion projection, credit display, and local SQLite history.
- `codex-quota` command-line interface with `doctor`, `status`, `serve`, and `service-unit` commands.
- Linux installer, bootstrap of a fresh Python virtual environment, systemd unit generation, health verification, lifecycle documentation, and a dry-run-first uninstaller.
- Python package metadata and package-relative web assets for installed use.

### Changed

- Extracted reusable quota normalization, metrics, configuration, environment, storage, Codex stdio adapter, and systemd-generation components from the initial prototype.
- Centralized runtime configuration and made installed-package data default to the user data directory while source checkouts retain local `data/` storage.
- Systemd deployment now starts the installed `codex-quota` executable and supports alternate service names.

### Security

- Generated systemd units use `NoNewPrivileges=true` and `PrivateTmp=true`; the installer defaults to localhost binding.
