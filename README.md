# FlightMargin

FlightMargin is a lightweight, local-first monitor for OpenAI Codex usage
limits, pacing, resets, purchased credits, and history.

> **Beta status:** `0.3.0-beta.1` is published as a GitHub prerelease with an
> intentionally unsigned Windows installer and SHA-256 checksum. Code signing
> is not a Beta 1 release gate.

Unofficial community tool. Not affiliated with or endorsed by OpenAI.

## What it shows

- 5-hour and Weekly quota windows with reset timing
- Weekly Pace and projected exhaustion
- Full Resets and purchased Credits when supplied by Codex
- Local SQLite History with a compact seven-day graph
- Windows tray visibility, optional start at login, and single-instance behavior
- Linux/headless CLI, browser dashboard, and systemd installation tools
- Local Settings, About metadata, and sanitized diagnostics
- Optional, default-off Mobile Relay upload of the latest normalized quota
  state and explicit mobile-device pairing

FlightMargin is intentionally Codex-focused. It has no telemetry,
notifications, transcript analytics, or token-cost accounting. Optional Mobile
Relay access is disabled by default and sends only the approved normalized
latest quota fields when the user enables it; local history and Codex
credentials never enter the relay.

## How it works

FlightMargin discovers the user's existing authenticated Codex CLI and reads
structured rate-limit information from its local app-server:

```text
FlightMargin -> codex app-server --stdio -> account/rateLimits/read
             -> local SQLite history -> dashboard and tray
             -> optional HTTPS Mobile Relay (latest normalized state only)
```

Codex is not bundled. FlightMargin does not ask for or store OpenAI passwords,
tokens, API keys, or `auth.json` contents. The Windows sidecar listens only on
an ephemeral `127.0.0.1` port.

## Windows desktop

The validated desktop target is Windows 11 x64 with Microsoft Edge WebView2
and an existing Codex CLI installation. Windows 10 has not yet been validated.

The published Beta 1 artifacts are named:

```text
FlightMargin-0.3.0-beta.1-Windows-x64.exe
FlightMargin-0.3.0-beta.1-Windows-x64.exe.sha256
```

The Beta 1 installer will be unsigned and Windows may show Unknown Publisher
or Microsoft Defender SmartScreen warnings. A published SHA-256 checksum is
required for verification. Signing and auto-update are deferred; see the
[Windows installation guide](docs/installation-windows.md).

Windows data is stored under:

```text
%LOCALAPPDATA%\FlightMargin
```

On first launch, if that directory does not exist and the legacy internal
`%LOCALAPPDATA%\Codex Quota Monitor` directory exists, FlightMargin copies the
existing `quota.db` and `desktop-preferences.json`. The old directory remains
untouched; logs and caches are not migrated.

## Linux/headless and browser

Linux uses the same dashboard, thresholds, history, Settings/About content,
and privacy model. The canonical CLI is `flightmargin`; the legacy
`codex-quota` alias remains available during the beta line. New generated
service installations default to `flightmargin.service`, while existing
`codex-quota.service` deployments can continue using their current explicit
configuration.

The browser service has no application-level authentication. Keep it on
localhost, a trusted private network, or a private VPN. See
[Linux installation](docs/installation-linux.md) and
[platform parity](docs/platform-parity.md).

## Optional Mobile Relay

Mobile Relay is disabled by default. Enabling it creates a dedicated
FlightMargin host credential, independently revocable from Codex/OpenAI
authentication, and synchronizes only the latest normalized quota state.
Windows protects the credential with current-user DPAPI. Linux stores it in a
mode-`0600` file under the FlightMargin application-data directory. Relay
outages do not interrupt local collection, history, dashboard, or tray use.
Pairing is user-initiated from Settings and creates a five-minute manual
code/QR session. The I-06A native iPhone companion and Mac/Simulator validation
are complete; I-06B real hosted-relay validation on a physical iPhone is next.
There is no TestFlight or App Store release, production signing configuration,
or public iPhone app. See
[the relay design](docs/mobile-relay-design.md) and
[iOS development handoff](docs/ios-development.md).

## Development

`app/version.py` is the single canonical version source. Tauri and Cargo
manifests are generated from it. Python package metadata normalizes the SemVer
prerelease `0.3.0-beta.1` to the PEP 440 form `0.3.0b1` in wheel filenames and
metadata.

Run the Python suite:

```powershell
$env:TEMP = "$PWD\.tmp-pytest"
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -m pytest -v
```

Prepare and validate the Windows shell:

```powershell
Set-Location desktop
npm ci
npm run prepare
cargo check --locked --manifest-path src-tauri\Cargo.toml
cargo test --locked --manifest-path src-tauri\Cargo.toml
node --check ..\app\static\app.js
node --check ..\app\static\settings.js
```

Build an unsigned local NSIS installer (this rebuilds the PyInstaller sidecar):

```powershell
Set-Location desktop
npm run tauri:build
```

The build does not publish, sign, tag, or create a GitHub Release.

## Post-Beta 1 development

The published FlightMargin `0.3.0-beta.1` artifact remains immutable. New work
is developed on milestone branches without changing its tag or release assets.
Multi-provider support, Claude/Gemini/Cursor support, transcript analytics,
token-cost accounting, notifications, iPhone distribution, and auto-update
remain possible future work based on user demand.

## Contributing, security, and release status

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Privacy](docs/privacy.md)
- [Public beta checklist](docs/public-beta-checklist.md)
- [Third-party license inventory](docs/third-party-licenses.md)

The public source repository is [gmstd66/flightmargin](https://github.com/gmstd66/flightmargin)
and issues are collected at [github.com/gmstd66/flightmargin/issues](https://github.com/gmstd66/flightmargin/issues).
The About page links to the public source and issue tracker. Sponsor links
remain deferred and are not present.

## License

FlightMargin is licensed under the GNU Affero General Public License v3.0 or
later (`AGPL-3.0-or-later`). See [LICENSE](LICENSE).
