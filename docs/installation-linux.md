# Codex Quota Monitor — Linux Installation

## Overview

Codex Quota Monitor currently supports Linux systems using systemd.

The application runs as a Python service, launches the locally installed Codex CLI, samples quota information, stores historical data in SQLite, and serves a local web dashboard.

The Linux installer can:

- validate the environment
- create a Python virtual environment
- upgrade pip
- install runtime dependencies
- generate a systemd service
- validate the generated service
- back up an existing service definition
- install or update the service
- enable automatic startup
- restart the application
- verify the health endpoint

The installer defaults to dry-run mode.

---

## 1. Prerequisites

The host needs:

- Linux
- systemd
- Python 3
- Python virtual-environment support
- OpenAI Codex CLI
- an authenticated Codex session
- Git
- sudo access for service installation

Check Python:

```bash
python3 --version
```

Check Git:

```bash
git --version
```

Check Codex:

```bash
codex --version
```

---

## 2. Codex authentication

Codex Quota Monitor does not manage OpenAI authentication itself.

It uses the authentication already available to the Codex CLI.

Before installing Codex Quota Monitor, verify that Codex works normally for the user account that will run the service.

For example:

```bash
codex
```

Complete the normal Codex sign-in flow if authentication is required.

The systemd service must run as a user whose HOME and Codex authentication state are accessible to Codex.

---

## 3. Obtain the repository

Clone:

```bash
git clone https://github.com/<owner>/<repository>.git
cd codex-quota-monitor
```

The repository is currently private.

Until the project is made public, GitHub authentication is required to clone it.

Possible authenticated Git workflows include:

- GitHub CLI authentication
- HTTPS credentials
- SSH authentication

---

## 4. Dry-run installation

The installer makes no system changes unless `--apply` is supplied.

Run:

```bash
scripts/install-linux.sh --dry-run
```

The dry run:

- checks prerequisites
- determines whether a virtual environment must be created
- runs application diagnostics
- generates the proposed systemd unit
- validates the unit
- prints the planned installation

If the virtual environment does not yet exist, dry-run mode does not create it.

---

## 5. Default installation

Run:

```bash
scripts/install-linux.sh --apply
```

Default configuration:

```text
Host:            127.0.0.1
Port:            8093
Sample interval: 60 seconds
Virtualenv:      <repository>/venv
Data:            <repository>/data
```

The default host is localhost for security.

The dashboard will be available at:

```text
http://127.0.0.1:8093
```

---

## 6. LAN installation

To make the dashboard available to devices on a trusted LAN, bind it to the machine's LAN address.

Example:

```bash
scripts/install-linux.sh \
  --host 192.168.1.50 \
  --port 8093 \
  --apply
```

The dashboard would then be available at:

```text
http://192.168.1.50:8093
```

Firewall configuration is outside the installer.

If a firewall is enabled, allow the chosen port only from trusted networks.

Do not expose Codex Quota Monitor directly to the public internet.

The dashboard currently has no application-level authentication.

---

## 7. Installer options

Show all options:

```bash
scripts/install-linux.sh --help
```

Important options include:

```text
--host ADDRESS
--port PORT
--sample-seconds SECONDS
--user USER
--group GROUP
--home PATH
--python PATH
--bootstrap-python PATH
--venv PATH
--codex PATH
--service-path PATH
--dev
--dry-run
--apply
```

### Custom virtual environment

```bash
scripts/install-linux.sh \
  --venv /opt/codex-quota-venv \
  --apply
```

### Existing Python environment

```bash
scripts/install-linux.sh \
  --python /path/to/venv/bin/python \
  --apply
```

When `--python` is explicitly supplied, the installer expects that executable to already exist.

### Development dependencies

```bash
scripts/install-linux.sh \
  --dev \
  --apply
```

This installs:

```text
requirements-dev.txt
```

instead of only the runtime requirements.

---

## 8. Environment diagnostics

After installation:

```bash
venv/bin/python -m app.cli doctor
```

A successful result ends with:

```text
Ready.
```

The doctor checks:

- operating system
- Python
- Codex CLI discovery
- Codex version
- writable data directory
- Codex app-server
- rate-limit API
- account plan
- 5-hour quota
- weekly quota

---

## 9. CLI quota status

Run:

```bash
venv/bin/python -m app.cli status
```

Example output:

```text
Codex Quota Monitor

5-hour: 25% used / 75% remaining
Weekly:  50% used / 50% remaining
Plan:    plus
Resets:  3 available
```

---

## 10. Service management

Status:

```bash
systemctl status codex-quota --no-pager -l
```

Check startup state:

```bash
systemctl is-enabled codex-quota
```

Check runtime state:

```bash
systemctl is-active codex-quota
```

Restart:

```bash
sudo systemctl restart codex-quota
```

Stop:

```bash
sudo systemctl stop codex-quota
```

Start:

```bash
sudo systemctl start codex-quota
```

Logs:

```bash
journalctl -u codex-quota -f
```

Recent logs:

```bash
journalctl \
  -u codex-quota \
  -n 100 \
  --no-pager
```

---

## 11. API health check

Default localhost installation:

```bash
curl -s \
  http://127.0.0.1:8093/api/health \
  | python3 -m json.tool
```

Expected structure:

```json
{
    "status": "ok",
    "version": "0.2.0",
    "collector": {
        "running": true
    },
    "sample_interval_seconds": 60
}
```

---

## 12. Upgrade

Enter the repository:

```bash
cd /path/to/codex-quota-monitor
```

Update the source:

```bash
git pull
```

Then rerun the installer using the same deployment configuration.

For a localhost installation:

```bash
scripts/install-linux.sh --apply
```

For a LAN installation, repeat the existing host and port:

```bash
scripts/install-linux.sh \
  --host 192.168.1.50 \
  --port 8093 \
  --apply
```

The installer:

1. updates Python dependencies
2. runs diagnostics
3. generates the new systemd unit
4. validates the unit
5. creates a timestamped backup of the current unit
6. installs the new unit
7. reloads systemd
8. restarts the service
9. verifies the health endpoint

---

## 13. Service backups

Before replacing an existing service, the installer creates backups similar to:

```text
/etc/systemd/system/codex-quota.service.backup.20260923-140722
```

These are not automatically deleted.

They can be used for manual rollback if necessary.

---

## 14. Manual service rollback

List available backups:

```bash
sudo ls -lt \
  /etc/systemd/system/codex-quota.service*
```

Restore one:

```bash
sudo cp \
  /etc/systemd/system/codex-quota.service.backup.TIMESTAMP \
  /etc/systemd/system/codex-quota.service

sudo systemctl daemon-reload
sudo systemctl restart codex-quota
```

Then verify:

```bash
systemctl status \
  codex-quota \
  --no-pager -l
```

---

## 15. Uninstall

The uninstall script defaults to dry-run mode:

```bash
scripts/uninstall-linux.sh
```

or:

```bash
scripts/uninstall-linux.sh --dry-run
```

To remove the systemd service:

```bash
scripts/uninstall-linux.sh --apply
```

By default, uninstall does not remove:

- quota history
- the Python virtual environment
- the repository
- Codex CLI
- Codex authentication

Optional cleanup flags are described by:

```bash
scripts/uninstall-linux.sh --help
```

---

## 16. Runtime data

The default SQLite database is:

```text
data/quota.db
```

This contains local quota history.

The database is excluded from Git.

Back it up before deleting runtime data if historical usage is important.

---

## 17. Security

Codex Quota Monitor currently has no application-level login.

Recommended configurations are:

- localhost only
- trusted private LAN
- private VPN

Avoid:

- public port forwarding
- exposing port 8093 directly to the internet
- running the service under an account that cannot access the authenticated Codex environment

The application does not store ChatGPT passwords or manually configured OpenAI API credentials.

---

## 18. Troubleshooting

### Codex not found

Check:

```bash
command -v codex
codex --version
```

Use an explicit path if needed:

```bash
scripts/install-linux.sh \
  --codex /path/to/codex \
  --apply
```

### Codex authentication failure

Run Codex interactively as the service user:

```bash
codex
```

Verify authentication before restarting Codex Quota Monitor.

### Python venv creation fails

On Debian or Ubuntu, the Python venv package may be required:

```bash
sudo apt install python3-venv
```

Then rerun:

```bash
scripts/install-linux.sh --apply
```

### Service does not start

Check:

```bash
systemctl status \
  codex-quota \
  --no-pager -l
```

and:

```bash
journalctl \
  -u codex-quota \
  -n 100 \
  --no-pager
```

### Health endpoint fails

For a default installation:

```bash
curl \
  http://127.0.0.1:8093/api/health
```

For LAN deployments, use the configured host.

### Port already in use

Inspect:

```bash
ss -ltnp
```

Choose another port:

```bash
scripts/install-linux.sh \
  --port 8094 \
  --apply
```

---

## Current scope

The Linux installer currently assumes:

- the repository has already been cloned
- Codex CLI is already installed
- Codex authentication already exists
- systemd is available

Automatic Codex CLI installation is intentionally not part of the installer at this stage.
