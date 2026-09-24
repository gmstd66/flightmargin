# Codex Quota Monitor — Project Status

This is the primary continuity and handoff document for future Codex sessions. Read it with `AGENTS.md`, then verify its summary against the current working tree, `git status`, `git log`, and the relevant implementation before changing the project. Git is the detailed engineering history; this document and `CHANGELOG.md` summarize it rather than replacing it.

## Purpose and current product state

Codex Quota Monitor is a local-first browser dashboard and CLI for monitoring OpenAI Codex quota usage through the locally authenticated Codex CLI. It reads `account/rateLimits/read` from `codex app-server --stdio`, persists local history, and serves a FastAPI dashboard.

The current package version is `0.2.0` (`pyproject.toml`). The project has moved beyond the original <private-host> prototype into a Linux-installable Python package with a generated systemd service. It is not an officially published package or release: do not tag, publish, or create a GitHub release without explicit approval.

## Architecture and modules

Runtime flow:

```text
browser / CLI → FastAPI or CLI commands → Codex app-server JSON-RPC
                                        → quota normalization and metrics
                                        → SQLite history → dashboard API
```

- `app/main.py`: FastAPI application, dashboard/API routes, lifecycle, and 60-second collector loop by default.
- `app/adapters/codex_stdio.py`: persistent `codex app-server --stdio` JSON-RPC adapter.
- `app/core/quota.py` and `app/core/metrics.py`: rate-limit normalization and derived dashboard metrics.
- `app/core/config.py`: centralized environment-driven configuration.
- `app/storage/sqlite_store.py`: SQLite schema and sample queries.
- `app/cli.py`: installed `codex-quota` CLI (`doctor`, `status`, `serve`, `service-unit`).
- `app/systemd.py`: portable systemd unit rendering.
- `scripts/install-linux.sh` and `scripts/uninstall-linux.sh`: dry-run-first Linux lifecycle tooling.

Web templates and static files are package-relative (`app/templates`, `app/static`) so they remain available after installation.

## Packaging, configuration, and storage

`pyproject.toml` defines the `codex-quota-monitor` Python project, version `0.2.0`, and the `codex-quota` console script. Runtime dependencies are FastAPI, Uvicorn, and Jinja2. The Linux installer installs the project into its selected virtual environment and systemd starts the installed `codex-quota` CLI.

Supported configuration variables are:

| Variable | Meaning | Default |
| --- | --- | --- |
| `CODEX_QUOTA_DATA_DIR` | Runtime data directory | source checkout: `<repo>/data`; installed package: `$XDG_DATA_HOME/codex-quota-monitor` or `~/.local/share/codex-quota-monitor` |
| `CODEX_QUOTA_DB` | SQLite database path | `<data-dir>/quota.db` |
| `CODEX_QUOTA_HOST` | Dashboard bind address | `127.0.0.1` |
| `CODEX_QUOTA_PORT` | Dashboard TCP port | `8093` |
| `CODEX_QUOTA_SAMPLE_SECONDS` | Sampling interval; minimum 10 | `60` |
| `CODEX_BIN` | Explicit Codex CLI executable | discovered as `codex` on `PATH` |

SQLite creates `quota_samples`, containing capture time; 5-hour and weekly usage/reset values; plan; reset-credit and balance data; and rate-limit/spend-control state. The database is local runtime data and excluded from Git.

## Linux installation and production facts

Linux support currently requires systemd, Python 3 with `venv`, an installed and authenticated Codex CLI, Git, and `sudo` for service installation. `scripts/install-linux.sh` validates the environment, can bootstrap a venv, installs the package, generates and validates a service unit, and on `--apply` enables, starts, and health-checks it. It defaults to dry run and localhost binding. `scripts/uninstall-linux.sh` defaults to dry run and preserves the repository, venv, data, Codex CLI, and Codex authentication unless explicit cleanup flags are used.

Verified production deployment facts (read-only unless explicitly approved):

- Checkout: `/opt/codex-quota`
- Service: `codex-quota.service`
- Port: `8093`
- Database: `/opt/codex-quota/data/quota.db`
- Runtime command: installed `codex-quota` CLI
- Service hardening: `NoNewPrivileges=true` and `PrivateTmp=true`

The production <private-host> deployment binds to its configured LAN address and is protected by the existing firewall rules described in `docs/private-deployment-record.md`. It has no application-level authentication; do not expose it to the public internet. Production changes, including the service, database, port, firewall, credentials, authentication state, or checkout, require explicit human approval.

For development, prefer `<private-development-path>/`, use temporary ports in `18000-18999`, and never use `8093` for a test instance. Temporary systemd services must begin `codex-quota-test-`; do not install them from `/tmp`, because `PrivateTmp=true` prevents the service from seeing host `/tmp` executables.

## Codex CLI integration

The application does not store ChatGPT passwords or use a separately configured OpenAI API key. It relies on the authentication available to the service user's Codex CLI. The adapter starts `codex app-server --stdio`, initializes JSON-RPC, and calls `account/rateLimits/read`. Quota windows are recognized by duration: 300 minutes (5-hour) and 10,080 minutes (weekly). `codex-quota doctor` verifies platform, Python, Codex discovery/version, writable data storage, app-server access, rate-limit access, plan, and both quota windows.

## Tests and completed work

`pytest` is configured to run the `tests/` suite. The documentation milestone validation completed with 56 passing tests. Coverage currently includes quota normalization and metrics, configuration defaults and overrides, environment checks, CLI parsing/status behavior, systemd generation, package metadata, and package-relative resources. Run `pytest -v` after changes; documentation milestones must also run `git diff --check`.

Git history records these completed capabilities:

- Initial known-working <private-host> baseline, documented and tagged `v0.1-baseline` before portability work.
- Core architecture extraction/refactoring plus baseline quota and metric tests.
- Environment doctor and user-facing CLI.
- Centralized configuration and portable systemd-unit generator.
- Linux installer, fresh-machine venv bootstrap, lifecycle documentation, and conservative uninstaller.
- Alternate systemd service names and isolated fresh-install-oriented deployment support.
- Package-relative templates/static resources, Python wheel/package metadata, and correct installed-package user data-directory behavior.
- Systemd execution through the packaged `codex-quota` CLI.
- Bounded-autonomy development policy.

## Branch workflow, caveats, and next work

Routine work belongs on `dev/productization`, not `main`. Before editing, fetch `origin`, ensure the local branch is synchronized with `origin/dev/productization`, and inspect the working tree. Complete milestones with tests, relevant documentation, a meaningful commit, a push to `origin/dev/productization`, and remote verification. Stop for a protected gate: merging to `main`, tagging or releasing, publication, production changes, destructive Git actions, or other decisions identified in `AGENTS.md`.

Known caveats:

- Linux/systemd is the currently supported deployment model; Windows, macOS, Docker, desktop, and tray/menu-bar implementations are not present.
- Codex CLI availability, its authenticated user context, and the app-server rate-limit response are external dependencies.
- The dashboard has no built-in authentication and should remain local, trusted-LAN, or private-VPN only.
- The service `WorkingDirectory` is the project root even though its executable is packaged; repository-based installation remains the documented workflow.

Near-term work is the next productization milestone after this documentation/governance milestone. The README roadmap identifies Docker deployment, desktop application, tray/menu-bar display, Windows, and macOS support; selecting a release plan, a package-publication plan, or a deployment-model change requires the appropriate human decision gate first.

## Instructions for future Codex sessions

1. Read `AGENTS.md`, this document, `CHANGELOG.md`, README, and the relevant technical documentation.
2. Verify branch, remote synchronization, package version, paths, commands, and tests from the current repository; do not treat this summary as proof when code disagrees.
3. Preserve protected production resources and use isolated development ports/services.
4. Update this document, the changelog, and any affected docs in the same milestone whenever practical; commit and push the completed milestone to `origin/dev/productization`.
