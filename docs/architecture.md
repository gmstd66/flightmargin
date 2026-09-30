# FlightMargin — Current Architecture

## Purpose

FlightMargin is a local-first browser dashboard and Windows desktop shell for
monitoring OpenAI Codex usage limits. The architecture predates and is retained
through the public identity migration.

The implementation began as a Linux/server prototype and now also includes a
Windows-first desktop shell plus optional Mobile Relay host synchronization.

## Data source

Quota data is read from the locally authenticated Codex CLI using:

`codex app-server --stdio`

The application initializes the Codex app-server JSON-RPC interface and requests:

`account/rateLimits/read`

The response currently provides:

- 5-hour usage window
- weekly usage window
- reset timestamps
- plan type
- credit balance
- available full reset credits
- rate-limit state

The application identifies quota windows by duration:

- 300 minutes = 5-hour window
- 10080 minutes = weekly window

## Application stack

- Python 3
- FastAPI
- Uvicorn
- Jinja2
- SQLite
- Vanilla JavaScript
- HTML/CSS

## Runtime flow

Browser
→ FastAPI
→ persistent Codex app-server subprocess
→ `account/rateLimits/read`
→ normalized quota data
→ SQLite history
→ API/dashboard

After a successful collector result and normal SQLite insertion, the optional
Mobile Relay coordinator receives the latest sample. When explicitly enabled,
it registers a dedicated host identity and sends only the allowlisted
normalized v1 fields over verified HTTPS. It keeps no upload history or queue;
relay failure is isolated from collection, local storage, and the dashboard.

Relay responsibilities remain separated under `app/mobile_relay/`:

- configuration and endpoint policy;
- DPAPI/Linux host identity storage;
- standard-library relay API transport;
- latest-only synchronization, bounded backoff, and pairing.

The reference server under `relay/` is development-only and excluded from the
normal wheel and Windows application package.

## Sampling

The backend samples Codex every 60 seconds.

The browser refreshes displayed values every 15 seconds from the local API.

Browser refreshes do not trigger additional Codex polling.

## Storage

Runtime history is stored in:

`data/quota.db`

The database is intentionally excluded from Git.

Current stored fields include:

- capture timestamp
- 5-hour percentage used
- 5-hour reset timestamp
- weekly percentage used
- weekly reset timestamp
- plan type
- available reset credits
- credit balance
- spend-control state
- rate-limit reached type

## Dashboard

The current dashboard provides:

- 5-hour usage gauge
- weekly usage gauge
- reset countdowns
- weekly pace indicator
- projected exhaustion
- available full reset credits
- purchased credit balance
- plan information
- semantic normal/warning/critical remaining-quota state
- persistent panel visibility
- 7-day historical usage graph
- daily X-axis divisions
- 4-hour chart gridlines
- manual refresh

## Platform model

Both Windows and Linux use the same Python collector, normalized API, database,
dashboard template, styles, and browser JavaScript. Platform-specific shells do
not reimplement quota calculations.

The shared application assumes:

- Codex CLI is already installed
- Codex CLI is already authenticated
- Codex is discoverable as `codex`
- SQLite filesystem access

Linux uses systemd and a browser/headless interface. Windows uses Tauri with a
PyInstaller sidecar, native tray/startup integration, and NSIS. Runtime
configuration is centralized in `app.core.config`; deployment-specific paths
can be supplied through environment variables and the installer-generated
systemd unit. See `platform-parity.md`.

## Security model

The application does not store ChatGPT passwords or manually managed API credentials.

It relies on the existing authenticated Codex CLI environment.

The dashboard currently has no application-level authentication and is intended for trusted local/LAN use only.
