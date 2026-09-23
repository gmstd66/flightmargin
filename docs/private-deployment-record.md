# <private-host> Deployment

## Host

Current production prototype:

- Host: <private-host>
- OS: Ubuntu 24.04
- LAN address: <private-lan-address>
- Application directory: `/opt/codex-quota`
- Dashboard port: TCP 8093

Port 8093 is reserved for Codex Quota Monitor on <private-host>.

## Service

The application runs under systemd:

`codex-quota.service`

The service:

- starts automatically at boot
- runs as user `<service-user>`
- launches Uvicorn
- binds specifically to `<private-lan-address>:8093`
- restarts on failure

## Firewall

UFW is enabled.

Default incoming policy:

`deny`

Allowed LAN access:

- SSH TCP 22 from `<private-lan-subnet>`
- Codex Quota TCP 8093 from `<private-lan-subnet>`

## Ubuntu sandbox configuration

Ubuntu's normal unprivileged user-namespace restriction is enabled:

`kernel.apparmor_restrict_unprivileged_userns = 1`

Codex app-server and its bubblewrap-based sandbox are working under this configuration.

## Data

SQLite runtime history:

`/opt/codex-quota/data/quota.db`

This database is not committed to Git.

## Git repository

Local repository:

`/opt/codex-quota`

GitHub:

`<owner>/<repository>`

Baseline tag:

`v0.1-baseline`

The baseline represents the known-working <private-host> prototype before portability refactoring.

