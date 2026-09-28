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
