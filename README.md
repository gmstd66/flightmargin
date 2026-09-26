# Codex Quota Monitor

Codex Quota Monitor is a lightweight, local-first monitor for Codex usage
limits, reset windows, purchased credits, and recent usage history. The first
planned public desktop target is Windows.

> **Public beta status:** release preparation is in progress. The repository is
> still private, the current Windows artifacts are unsigned internal builds,
> and no public installer has been released.

Unofficial community tool. Not affiliated with or endorsed by OpenAI.

## Screenshot

The public screenshot will be added after the product name and branding review
are approved. Screenshots must not contain account identity, private paths, or
other personal information.

## Features

- 5-hour and weekly quota gauges with reset timing
- Weekly pace and projected exhaustion information
- Purchased-credit and full-reset information
- Local SQLite history with a compact seven-day graph
- Windows tray indicators for weekly, 5-hour, and purchased-credit values
- Optional start at login, close to tray, and single-instance behavior
- Local Settings, About information, and sanitized copyable diagnostics
- Linux/headless CLI, FastAPI dashboard, and systemd installation tools

## How it works

The application discovers the user's existing Codex CLI and asks its local
`app-server` for structured rate-limit information:

```text
Codex Quota Monitor -> codex app-server --stdio -> account/rateLimits/read
                    -> local SQLite history -> dashboard and tray
```

Codex is not bundled. Users must install and authenticate Codex independently.
The desktop sidecar listens only on an ephemeral `127.0.0.1` port.

## Windows beta requirements

Only the following public-beta target has been validated:

- Windows x64
- Windows 11
- Microsoft Edge WebView2 Runtime
- an existing Codex CLI installation
- an existing authenticated Codex/ChatGPT session available to that CLI

Windows 10 has not yet been validated and is not currently claimed as
supported. See [Windows public beta](docs/windows-public-beta.md) for
installation, usage, update, uninstall, troubleshooting, and limitations.

## Windows installation

Once a public beta is approved, download the NSIS `-setup.exe` and its SHA-256
file from the matching GitHub prerelease. Verify the checksum, fully Quit any
running Codex Quota Monitor instance from the tray, and run the installer.

The first beta will use manual downloads. Tauri auto-update is intentionally
deferred. Until code signing is available, Windows may show an unidentified
publisher or SmartScreen warning; do not install an artifact from any location
other than the project's eventual GitHub Releases page.

## Data and privacy

On Windows, history, preferences, and logs stay under:

```text
%LOCALAPPDATA%\Codex Quota Monitor
```

Codex Quota Monitor reuses the authentication already managed by Codex. It does
not manage or store OpenAI passwords, tokens, or `auth.json` content. It has no
remote telemetry. See [Privacy](docs/privacy.md) for the complete data summary.

## Linux/headless edition

The Linux/systemd edition remains available separately from the Windows beta.
It uses the same quota cards, thresholds, history, panel-visibility controls,
and browser About/diagnostics as the Windows dashboard. Linux-native startup
and logs remain systemd concerns; Windows tray and native-window behavior do
not apply. The browser service has no application-level authentication and must
remain on localhost, a trusted private network, or a private VPN. See
[Linux installation](docs/installation-linux.md) and
[Platform parity](docs/platform-parity.md).

## Development

The canonical version is defined in `app/version.py`. The current internal
development line remains `0.2.0`; `0.3.0-beta.1` is only a proposed first public
version until the owner approves a version change.

Run the Python suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Prepare and check the Windows shell:

```powershell
Set-Location desktop
npm ci
npm run prepare
cargo check --locked --manifest-path src-tauri\Cargo.toml
cargo test --locked --manifest-path src-tauri\Cargo.toml
```

Build an unsigned local Windows installer:

```powershell
Set-Location desktop
npm run tauri:build
```

The build command rebuilds the PyInstaller sidecar before Tauri packages NSIS,
so current dashboard assets are always embedded. It does not publish anything.
See [Desktop implementation](docs/desktop-implementation.md) for prerequisites
and architecture details.

## Contributing and security

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Public beta checklist](docs/public-beta-checklist.md)
- [Third-party license inventory](docs/third-party-licenses.md)

Outside contributions must wait until the repository is public and the project
license is selected. Security reports should use the private process described
in `SECURITY.md`, not a public issue containing exploit details.

## Distribution model

The project is intended to remain free and open source, with no paid feature
tier. Voluntary sponsorship through GitHub Sponsors is planned after a real
sponsorship destination exists. Public Windows installers are expected to use
GitHub Releases, with free OSS code signing pursued through SignPath Foundation
if the project qualifies.

No `FUNDING.yml`, Sponsor link, or auto-updater is enabled yet.

## License

The owner has selected **AGPLv3-or-later**. The public-license transition is not
complete: no `LICENSE` file is added in milestone 6.20B, and the repository must
not accept external contributions until that file and contribution terms are
approved in the public identity milestone. See
[License decision](docs/license-decision.md).
