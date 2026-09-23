# Codex Quota Monitor — Current Architecture

## Purpose

Codex Quota Monitor is a local-first browser dashboard for monitoring OpenAI Codex usage limits.

The current implementation is the original Linux/server prototype running on the <private-host> host.

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
- plan information
- 7-day historical usage graph
- daily X-axis divisions
- 4-hour chart gridlines
- manual refresh

## Current portability limitations

The current prototype assumes:

- Codex CLI is already installed
- Codex CLI is already authenticated
- Codex is discoverable as `codex`
- Linux host
- systemd for autostart
- local browser/network access
- SQLite filesystem access

Some code currently contains deployment-specific paths and assumptions that will be removed during the portable-core refactor.

## Security model

The application does not store ChatGPT passwords or manually managed API credentials.

It relies on the existing authenticated Codex CLI environment.

The dashboard currently has no application-level authentication and is intended for trusted local/LAN use only.

