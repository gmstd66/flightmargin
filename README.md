# Codex Quota Monitor

Codex Quota Monitor is a local-first browser dashboard for monitoring OpenAI Codex usage limits.

It reads structured quota information from the locally authenticated Codex CLI and stores historical usage locally in SQLite.

## Features

- 5-hour Codex quota monitoring
- Weekly quota monitoring
- Exact reset times
- Sustainable usage pace calculation
- Projected quota exhaustion
- Full-reset credit display
- 60-second backend sampling
- Manual refresh
- SQLite history
- Rolling 7-day graph
- Daily chart divisions
- 4-hour chart gridlines
- Local browser dashboard
- Environment diagnostics
- Command-line status view
- Portable systemd service generation
- Linux installer
- Fresh-machine Python virtual environment bootstrap

## How it works

Codex Quota Monitor uses the locally authenticated Codex CLI:

```text
codex app-server --stdio
```

It requests:

```text
account/rateLimits/read
```

Quota windows are identified by duration:

```text
300 minutes   = 5-hour window
10080 minutes = weekly window
```

The application does not require a separately managed OpenAI API key.

## Requirements

Current Linux support requires:

- Linux with systemd
- Python 3
- Python `venv` support
- OpenAI Codex CLI installed
- Codex CLI already authenticated
- `sudo` access for systemd installation

The installer creates the application virtual environment and installs Python dependencies when needed.

## Quick start

Clone the repository:

```bash
git clone https://github.com/<owner>/<repository>.git
cd codex-quota-monitor
```

Because the repository is currently private, GitHub authentication is required.

Confirm Codex works:

```bash
codex --version
codex
```

If necessary, complete the normal Codex authentication flow before installing Codex Quota Monitor.

Run an installation dry run:

```bash
scripts/install-linux.sh --dry-run
```

Install a local-only dashboard:

```bash
scripts/install-linux.sh --apply
```

The default dashboard address is:

```text
http://127.0.0.1:8093
```

For LAN access, bind to an appropriate address on the machine:

```bash
scripts/install-linux.sh \
  --host 192.168.1.50 \
  --port 8093 \
  --apply
```

Do not expose the dashboard directly to the public internet. It currently has no application-level authentication.

## Diagnostics

Run:

```bash
venv/bin/python -m app.cli doctor
```

or:

```bash
venv/bin/python -m app.doctor
```

A healthy installation should finish with:

```text
Ready.
```

## Current quota

```bash
venv/bin/python -m app.cli status
```

## Service management

Check status:

```bash
systemctl status codex-quota
```

Restart:

```bash
sudo systemctl restart codex-quota
```

Follow logs:

```bash
journalctl -u codex-quota -f
```

## Upgrade

From the repository:

```bash
git pull
scripts/install-linux.sh --apply
```

The installer updates Python dependencies, creates a timestamped backup of the existing systemd unit, regenerates the service definition, restarts the service, and verifies the health endpoint.

## Uninstall

Run:

```bash
scripts/uninstall-linux.sh
```

The uninstall script defaults to a dry run.

To remove the systemd service:

```bash
scripts/uninstall-linux.sh --apply
```

Runtime data and the repository are preserved by default.

See:

```text
docs/installation-linux.md
```

for the complete installation, upgrade, uninstall, and troubleshooting guide.

## Data and privacy

Quota history is stored locally in:

```text
data/quota.db
```

The database is excluded from Git.

Codex Quota Monitor does not store ChatGPT passwords or require a separately configured API credential. It relies on the authentication already used by the Codex CLI.

## Security

The dashboard currently has no built-in authentication.

Recommended deployment:

- localhost, or
- a trusted private LAN, or
- a private VPN

Do not directly port-forward the dashboard to the public internet.

## Development

Run tests:

```bash
source venv/bin/activate
pytest -v
```

### Local release-artifact check

The canonical application version is defined in:

```text
app/version.py
```

Build one local wheel without publishing it:

```bash
PYTHON=venv/bin/python scripts/build-release.sh
```

Verify its metadata, console entry point, and packaged dashboard resources:

```bash
venv/bin/python scripts/verify-release.py dist
```

Run the complete release check (tests, wheel build, artifact verification, and an isolated installed-wheel runtime check):

```bash
PYTHON=venv/bin/python scripts/check-release.sh
```

The complete check uses a disposable virtual environment and isolated application-data directory, runs the real Codex `doctor` and `status` checks, and starts the installed server on port `18097` by default. Override the development port with `CODEX_QUOTA_RELEASE_PORT` in the `18000-18999` range. The resulting local wheel is retained in `dist/`; nothing is tagged or published.

Current architecture documentation:

```text
docs/architecture.md
```

<private-host> deployment documentation:

```text
docs/private-deployment-record.md
```

## Roadmap

Planned work includes:

- Docker deployment
- desktop application
- tray/menu-bar quota display
- Windows support
- macOS support

Docker deployment feasibility, including Codex authentication and sandbox constraints, is documented in:

```text
docs/docker-feasibility.md
```

Native desktop feasibility, including the proposed Windows-first architecture, is documented in:

```text
docs/desktop-feasibility.md
```

The internal desktop prototype structure, local sidecar build instructions, and required Windows validation checklist are documented in:

```text
docs/desktop-implementation.md
```

## License

A license will be selected before public release.
