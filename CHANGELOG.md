# Changelog

Notable changes to Codex Quota Monitor are documented here. This file summarizes product-facing history; Git retains the detailed engineering history.

## Unreleased

### Added

- Project continuity and milestone-handoff documentation.

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
