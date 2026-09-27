# FlightMargin — Project Status

Updated: 2026-09-27

Branch: `dev/productization`

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

The repository remains private. The beta has not been tagged, published,
signed, or released. Auto-update is deferred. Source, issue, and Sponsor links
remain hidden until real public destinations exist.

FlightMargin is licensed `AGPL-3.0-or-later`; the standard GNU AGPL v3 text is
present in `LICENSE`. Third-party license notices remain separately inventoried.

Unofficial community tool. Not affiliated with or endorsed by OpenAI.

## Architecture

The approved architecture is unchanged:

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
- `app/cli.py`: `flightmargin` CLI and legacy `codex-quota` alias.
- `app/systemd.py`: systemd unit rendering.
- `desktop/`: Tauri 2 shell, PyInstaller sidecar build, tray/startup behavior,
  and current-user NSIS packaging.

The Windows shell communicates with its sidecar on an OS-assigned loopback
port. The Linux browser deployment has no application-level authentication and
must stay on localhost or a trusted private network.

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
- The private GitHub repository retains its current name. `flightmargin` is
  the intended publication-time repository name if it remains available and
  is separately approved.

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

## Linux production protection

The existing production deployment remains protected and unchanged:

- checkout `/opt/codex-quota`;
- service `codex-quota.service`;
- port `8093`;
- database `/opt/codex-quota/data/quota.db`;
- production configuration, firewall, service user, permissions, Codex
  authentication, and credentials.

No 6.20D.1 action may migrate or alter those resources. Linux development uses
an isolated checkout, ports `18000-18999`, and temporary service names beginning
`codex-quota-test-`.

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

The new bundle identifier intentionally distinguishes FlightMargin from the
internal 0.2.0 application, so an old build may need explicit uninstall and may
temporarily coexist. The user-data copy prevents silent loss of history and
preferences.

## About, privacy, and security

About reports FlightMargin, canonical version, Beta status, detected Codex CLI
version, OS, architecture, and sanitized data/log paths. It states that local
history/preferences/logs are stored locally, the existing authenticated Codex
CLI is used, credentials are not managed or stored, telemetry is absent, the
license is AGPLv3-or-later, and the app is unofficial. Public action links stay
hidden.

Logs contain concise lifecycle/errors only, rotate at 1 MB, and retain one
prior file. Diagnostics exclude account identity, quota payloads, credentials,
and raw authentication content.

## Feature freeze

Beta 1 adds no multi-provider support, Claude/Gemini/Cursor integrations,
session transcript analytics, token-cost accounting, notifications, mobile
companion, remote monitoring, or auto-update. Those remain possible post-beta
work based on demand. Bug, security, release-blocker, and migration fixes are
allowed.

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

## Remaining publication gates

- human review of this identity/migration milestone;
- history sanitation is **LOCAL SANITIZED HISTORY VALIDATED — REMOTE UPDATE
  PENDING** in `docs/history-sanitation-plan.md`; the private candidate has an
  identical pre/post rewrite HEAD tree, clean privacy/secret/integrity scans,
  preserved topology and dates, and complete Python/Rust/JavaScript/package
  validation;
- separate approval for the exact atomic force-with-lease remote update;
- public repository rename/visibility approval and final privacy scan;
- code-signing implementation and signed-artifact validation;
- public tag, package/installer publication, and GitHub Release approval;
- real public source, issue-reporting, security-contact, and Sponsor URLs.

No remote history update, merge to `main`, production deployment, tag, release,
public visibility change, or signing submission is authorized yet.
