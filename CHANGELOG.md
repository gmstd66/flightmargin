# Changelog

Notable changes to Codex Quota Monitor are documented here. This file summarizes product-facing history; Git retains the detailed engineering history.

## Unreleased

### Added

- Project continuity and milestone-handoff documentation.
- Reproducible local wheel build, artifact verification, and isolated installed-wheel release check scripts.
- Docker deployment feasibility findings and authentication-model investigation.
- Native desktop architecture feasibility findings and a Windows-first implementation proposal.
- Windows-first desktop prototype: Tauri 2 shell scaffold, PyInstaller sidecar build, loopback readiness protocol, desktop data paths, and cross-platform Codex discovery.
- Native Windows internal validation for the Tauri/PyInstaller desktop prototype, including unsigned MSI and NSIS artifacts, installed-app startup, host Codex discovery, authenticated quota collection, and app-data persistence.
- Windows beta desktop lifecycle: tray controls, single-instance activation, opt-in start-at-login, bounded local shell logs, and a repeatable Windows beta checklist.
- Owner GUI/product review walkthrough for the internal Windows desktop build.
- Compact configurable Windows dashboard with persisted panel visibility and quota-state colors.

### Changed

- Recorded the planned free, open-source distribution model: voluntary GitHub Sponsors support, GitHub Releases for future public installers, and a preference for qualifying free open-source code signing.
- Fixed Windows sidecar startup by passing the pre-bound loopback socket directly to Uvicorn.
- Added Windows Tauri icon configuration, current shell-plugin compatibility, clear sidecar-startup and collector diagnostics, and process-tree shutdown for PyInstaller one-file sidecars.
- Selected a current-user NSIS installer as the internal beta path and preserved per-user SQLite data on normal uninstall and upgrade.
- Standardized the dashboard title on Codex Quota Monitor and made collector status updates accessible to screen readers.
- Simplified the owner-reviewed Windows dashboard to a fixed compact responsive layout with visibility-only customization. Drag/reorder, arbitrary resizing, persisted geometry, and obsolete Settings controls were removed; schema 4 resets incompatible layout geometry while preserving unrelated preferences.
- Restored the Weekly History graph immediately when a hidden panel is shown and accepted decimal sidecar percentages when updating the numeric Windows tray indicators.
- Opened Settings in a focused, DPI-aware native window beside the dashboard and added Windows hidden-icons guidance for quota indicators.
- Removed the legacy in-dashboard Settings fallback in favor of a dedicated native-window page, and tightened three-digit tray rendering so `100` remains fully visible.

- Made `app.version.__version__` the canonical application version used by setuptools metadata, the CLI, API responses, and Codex app-server client identification.

## 0.2.0

### Added

- Local-first browser dashboard for 5-hour and weekly Codex quota monitoring, reset timing, sustainable pace, exhaustion projection, credit display, and local SQLite history.
- `codex-quota` command-line interface with `doctor`, `status`, `serve`, and `service-unit` commands.
- Linux installer, bootstrap of a fresh Python virtual environment, systemd unit generation, health verification, lifecycle documentation, and a dry-run-first uninstaller.
- Python package metadata and package-relative web assets for installed use.

### Changed

- Extracted reusable quota normalization, metrics, configuration, environment, storage, Codex stdio adapter, and systemd-generation components from the initial prototype.
- Centralized runtime configuration and made installed-package data default to the user data directory while source checkouts retain local `data/` storage.
- Systemd deployment now starts the installed `codex-quota` executable and supports alternate service names.

### Security

- Generated systemd units use `NoNewPrivileges=true` and `PrivateTmp=true`; the installer defaults to localhost binding.
