# Codex Quota Monitor — Project Status

This is the primary continuity and handoff document for future Codex sessions. Read it with `AGENTS.md`, then verify its summary against the current working tree, `git status`, `git log`, and the relevant implementation before changing the project. Git is the detailed engineering history; this document and `CHANGELOG.md` summarize it rather than replacing it.

## Purpose and current product state

Codex Quota Monitor is a local-first browser dashboard and CLI for monitoring OpenAI Codex quota usage through the locally authenticated Codex CLI. It reads `account/rateLimits/read` from `codex app-server --stdio`, persists local history, and serves a FastAPI dashboard.

The current package version is `0.2.0`, canonically defined by `app/version.py`. Setuptools reads that value dynamically for project metadata, and the CLI, API, and Codex app-server client use the same source. The project has moved beyond the original <private-host> prototype into a Linux-installable Python package with a generated systemd service. It is not an officially published package or release: do not tag, publish, or create a GitHub release without explicit approval.

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

`pyproject.toml` defines the `codex-quota-monitor` Python project and dynamically obtains its version from `app.version.__version__`; it also defines the `codex-quota` console script. Runtime dependencies are FastAPI, Uvicorn, and Jinja2. The Linux installer installs the project into its selected virtual environment and systemd starts the installed `codex-quota` CLI.

Local release-artifact workflow (no publication):

- `scripts/build-release.sh` cleans `dist/`, builds exactly one local wheel with `python -m pip wheel`, and prints its path.
- `scripts/verify-release.py dist` confirms the expected normalized wheel name/version, wheel metadata, `codex-quota` entry point, and required template/static files.
- `scripts/check-release.sh` runs the test suite, build, verification, and a temporary out-of-tree virtual-environment check. It verifies imports are from `site-packages`, the CLI version, real Codex `doctor`/`status`, isolated storage, server health, dashboard HTML, and static resources on a configurable `18000-18999` port (default `18097`). The temporary environment and test data are removed on completion; `dist/` retains the local artifact.

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

`pytest` is configured to run the `tests/` suite. Desktop coverage includes platform data/log paths, Codex discovery, loopback socket/readiness behavior, canonical version templates, and the existing dashboard/API behavior. Run `pytest -v` after changes; release-facing work should also run `scripts/check-release.sh` and `git diff --check`.

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
- Milestone 6.14: single-source versioning and a reproducible local wheel build, artifact verification, and isolated installed-artifact validation workflow.
- Milestone 6.15: Docker feasibility and approved deferral of self-contained Docker distribution.
- Milestone 6.16: native desktop feasibility, approved Windows-first Tauri/PyInstaller/FastAPI-sidecar prototype, platform-specific data paths, Codex discovery fallbacks, dynamic loopback readiness, Linux sidecar validation, and first Windows-native validation. On Windows 11, the built and installed unsigned Tauri artifact started the PyInstaller sidecar on an ephemeral loopback port, discovered authenticated host Codex through the npm wrapper, served quota/dashboard resources, persisted `%LOCALAPPDATA%\Codex Quota Monitor\quota.db`, and exited without sidecar residue. See `docs/desktop-implementation.md`.
- Milestone 6.17: Windows beta polish adds tray/background lifecycle, single-instance activation, opt-in start-at-login, controlled startup/crash diagnostics, bounded local shell logs, a current-user NSIS beta installer preference, and `docs/windows-beta.md` for repeatable validation. Public signing, update distribution, and release approval remain separate gates.
- Milestone 6.18: prepares the current Windows desktop beta for owner GUI/product review, with a documented UI inventory and review walkthrough. Public release, license, signing, and auto-update decisions remain deferred.
- Milestone 6.19D: owner-review corrections targeted a 600×450 desktop window,
  introduced direct pointer movement/resizing and schema-3 geometry, invalidated
  stale WebView assets, and marked the release Tauri executable as a Windows
  GUI-subsystem application. Subsequent owner testing rejected the dynamic
  layout because it remained unstable and disproportionately complex.
- Milestone 6.19E: owner testing deliberately simplified the dashboard to a
  fixed compact responsive layout. Drag/reorder, arbitrary panel resizing, and
  stored geometry were removed because their complexity and unstable layouts
  outweighed their usefulness. Schema 4 retains only stable panel visibility,
  restores all panels for schema-2/schema-3 users, and preserves unrelated
  desktop preferences such as the tray-indicator choice.
- Milestone 6.19F native validation confirmed the fixed 600×450 dashboard,
  schema-4 visibility persistence, dense panel reflow, and windowless startup.
  It also found two localized defects: restoring Weekly History did not redraw
  its hidden canvas, and decimal sidecar percentages made numeric tray icons
  remain unavailable. Source fixes and regression tests are complete; a fresh
  Windows artifact must still be built and visually revalidated.
- Final desktop UX refinement: Settings now opens as a single native window
  adjacent to the dashboard, with DPI-aware right/left placement and monitor
  work-area clamping. Its quota-indicator option includes concise Windows
  hidden-icons guidance; Windows remains responsible for icon placement.
- Owner validation found that the retained modal fallback could mask an
  unavailable global Tauri bridge and that the original three-digit tray glyphs
  overlapped at `100`. Settings now has a dedicated native-window page with no
  dashboard overlay fallback, and the 32x32 tray renderer uses a non-overlapping
  compact three-digit layout.
- The Windows tray model now adds a green purchased-Credits indicator to the
  normal application, blue Weekly, and purple 5-hour icons. It floors positive
  balances to whole credits, renders balances above 999 as `999+`, preserves
  the exact whole balance in the tooltip, and shares the existing collector
  sample and Settings lifecycle.

## Branch workflow, caveats, and next work

Routine work belongs on `dev/productization`, not `main`. Before editing, fetch `origin`, ensure the local branch is synchronized with `origin/dev/productization`, and inspect the working tree. Complete milestones with tests, relevant documentation, a meaningful commit, a push to `origin/dev/productization`, and remote verification. Stop for a protected gate: merging to `main`, tagging or releasing, publication, production changes, destructive Git actions, or other decisions identified in `AGENTS.md`.

## Product and distribution direction

Codex Quota Monitor is intended to remain free to use and become open source. The planned sustainability model is voluntary donations and sponsorship only, initially through GitHub Sponsors; there will be no paywall or paid feature tier. Public installers and downloads are expected to be distributed through GitHub Releases when the project is ready for public release.

The exact open-source license is intentionally unresolved. GPL, AGPL, or a related option are the current likely direction, but no license file or final license choice has been made. Before public distribution, pursue a free open-source Windows signing path such as SignPath Foundation if the project qualifies. Paid code-signing should be considered only if free signing is unavailable and the project justifies the expense.

The remaining product/distribution decisions are: the exact license; the first public release version; final GUI and product review; whether and when to enable Tauri auto-update; and the final code-signing implementation once repository and public-license status are ready. Tauri auto-update remains optional and deferred until after GUI/product review. These decisions do not authorize making the repository public, creating a release, publishing installers, or changing runtime behavior.

Known caveats:

- Linux/systemd is the currently supported deployment model. The Windows-first desktop application is internal/beta ready but not a supported public distribution; signing, auto-update, public release packaging, and broad Windows compatibility validation remain pending. Docker feasibility was investigated in milestone 6.15 and self-contained Docker remains deferred; see `docs/docker-feasibility.md`.
- Codex CLI availability, its authenticated user context, and the app-server rate-limit response are external dependencies.
- The dashboard has no built-in authentication and should remain local, trusted-LAN, or private-VPN only.
- The service `WorkingDirectory` is the project root even though its executable is packaged; repository-based installation remains the documented workflow.

Docker decision: self-contained Docker distribution is deferred because the current Codex app-server sandbox is not container-friendly under the tested Docker security profile. A host-bridge architecture is not currently justified. Native systemd remains the Linux/headless deployment model. Revisit Docker only if Codex gains a supported container-friendly execution model. See `docs/docker-feasibility.md` for the evidence.

Desktop decision status: milestone 6.16 approved and implemented a Windows-first Tauri 2 shell with a PyInstaller-packaged Python sidecar and loopback FastAPI, preserving the current dashboard and Codex integration. Native Windows validation now covers the sidecar, Tauri compilation, unsigned MSI/NSIS artifacts, installed-app launch, authenticated Codex quota reads, app-data persistence, failure diagnostics, and sidecar-tree shutdown. See `docs/desktop-feasibility.md` and `docs/desktop-implementation.md`. The README roadmap also identifies tray/menu-bar enhancements, macOS, and other future support; selecting a release or package-publication plan likewise requires the appropriate human decision gate first.

## Instructions for future Codex sessions

1. Read `AGENTS.md`, this document, `CHANGELOG.md`, README, and the relevant technical documentation.
2. Verify branch, remote synchronization, package version, paths, commands, and tests from the current repository; do not treat this summary as proof when code disagrees.
3. Preserve protected production resources and use isolated development ports/services.
4. For release-facing work, use `scripts/check-release.sh` with a development port, inspect `dist/`, and remember that a verified local wheel is not a tagged, published, or GitHub release.
5. Update this document, the changelog, and any affected docs in the same milestone whenever practical; commit and push the completed milestone to `origin/dev/productization`.
