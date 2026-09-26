# FlightMargin identity migration inventory

Milestone: 6.20D.1

Audit date: 2026-09-26

Baseline: `381b8e5608ce77576e26730fd5776c1fcd0b2b1b`

This inventory was completed before the rename was implemented. The migration
is intentionally limited to product identity, versioning, licensing, and the
small compatibility changes required to preserve existing users. It is not a
general refactor.

## Classification

- **A — public-facing identity:** rename to FlightMargin now.
- **B — stable internal compatibility identifier:** retain during the beta
  line unless a later, separately reviewed migration provides user value.
- **C — legacy compatibility path/name:** recognize or retain so existing
  installations continue to work.
- **D — historical/documentation reference:** preserve when it describes an
  old release; otherwise update to the current identity.
- **E — production-specific Linux identifier:** document but do not alter.

## Inventory and decisions

| Surface | Current occurrence | Class | 6.20D.1 decision |
| --- | --- | --- | --- |
| Browser/dashboard and Settings | `Codex Quota Monitor` in HTML titles, headings, About, FastAPI metadata, CLI and diagnostics | A | Show `FlightMargin`; keep quota vocabulary literal. |
| Product description and disclaimer | README, About, browser placeholder, docs | A | Use the approved local-first Codex-monitor description and retain the explicit unofficial/no-endorsement disclaimer. |
| Tauri product and windows | `productName`, main/Settings titles, tray tooltips and startup/error copy | A | Rename to `FlightMargin`. |
| Tauri package/main executable | Rust package `codex-quota-monitor-desktop` | A | Rename the package to `flightmargin-desktop`, producing `flightmargin-desktop.exe`. |
| Tauri bundle identifier | `com.codexquotamonitor.desktop` | A | Establish `io.github.gmstd66.flightmargin`, grounded in the current GitHub owner namespace rather than an owned-domain claim. This intentionally creates a distinct pre-public application identity. |
| NSIS identity | Product name and Start Menu folder `Codex Quota Monitor` | A | Rename to `FlightMargin`; expect the new bundle identity to install separately from the internal 0.2.0 build. |
| Windows data | `%LOCALAPPDATA%\Codex Quota Monitor` | C | Canonicalize on `%LOCALAPPDATA%\FlightMargin`. On first launch only, if the new directory is absent, atomically copy `quota.db` and `desktop-preferences.json` from the legacy directory. Preserve the legacy directory and do not copy logs or caches. |
| Windows desktop sidecar | `codex-quota-backend.exe`, Tauri `externalBin`, readiness prefix `CODEX_QUOTA_DESKTOP_PORT` | B | Retain. These are packaged implementation details and keeping them avoids an unrelated process-lifecycle/installer-hook migration. |
| Runtime environment | `CODEX_QUOTA_*`, `CODEX_BIN` | B | Retain. They are existing automation and deployment interfaces, not public branding. |
| Browser preference channel | `codex-quota-preferences` | B | Retain as an internal same-origin channel name; changing it provides no user benefit. |
| Python import package | `app` | B | Retain. Renaming module paths would add risk without changing public identity. |
| Python distribution | `codex-quota-monitor` | A | Rename to `flightmargin`; keep one canonical version in `app/version.py`. |
| Python CLI | `codex-quota` | C | Add canonical `flightmargin`; retain `codex-quota` as a beta-line compatibility alias to the same entry point. |
| Linux installed-user data | `$XDG_DATA_HOME/codex-quota-monitor` or `~/.local/share/codex-quota-monitor` | C | Canonicalize new installed-user defaults on `flightmargin`; copy the persistent database and preferences from the legacy directory only when the new directory is absent. Source-checkout `data/` and explicit environment overrides remain unchanged. |
| Linux systemd generator | Description `Codex Quota Monitor`; caller-selected CLI | A/B | Brand the description as FlightMargin and prefer the new CLI for new installs. Preserve support for caller-selected legacy CLI paths. |
| Linux install/uninstall scripts | default `codex-quota.service`, legacy CLI path, old product copy | C | Use `flightmargin.service` and `flightmargin` for new defaults. Continue accepting `--service-name codex-quota` and explicit legacy CLI paths for existing installs. |
| Protected production Linux | `/opt/codex-quota`, `codex-quota.service`, port `8093`, production database/configuration | E | No change. The production deployment is not migrated by this milestone. |
| Distribution/release artifacts | wheel prefix, Windows workflow artifact, installer/checksum naming | A | Use FlightMargin/`flightmargin` naming and keep the workflow manual and nonpublishing. |
| Version | canonical `0.2.0`, generated Cargo/Tauri mirrors, docs/checks | A/D | Set the canonical version to `0.3.0-beta.1`; regenerate mirrors and preserve `0.2.0` only in release history and transition notes. |
| License | selected but unapplied AGPLv3-or-later | A | Add the standard GNU AGPL v3 text as `LICENSE` and use SPDX `AGPL-3.0-or-later` in project/package metadata. |
| README and current operational/release docs | Current old-name copy and pending-decision text | A/D | Rebrand current guidance and resolve the approved name/version/license decisions. Preserve old-name references only where needed to explain migration/history. |
| Historical milestone records | Changelog 0.2.0, old feasibility/validation observations | D | Keep technically meaningful old-release references, labeling them as the legacy/internal identity where ambiguity is possible. |
| Repository and checkout name | private GitHub `codex-quota-monitor`, local checkout path | B/C | Do not rename in this milestone. Intended future repository name is `flightmargin`, subject to availability and publication approval. |
| Tests and fixtures | Old product, path, package, version, and installer assertions | A/C | Update public assertions and add explicit migration/idempotence plus legacy-alias coverage. Keep production-path fixtures unchanged. |

## Installer transition expectation

Changing the Tauri identifier before the first public release is safer than
carrying the internal identifier into the public line. The old internal 0.2.0
application and FlightMargin may therefore coexist until the old build is
explicitly uninstalled. The copy-only data migration prevents silent history
or preference loss, and normal uninstall behavior must continue to preserve
both old and new user-data directories.

## Windows validation result

The native `0.3.0-beta.1` NSIS package installed FlightMargin beside the
existing internal 0.2.0 application. Both install directories, Start Menu
entries, and uninstall records remained distinct. The FlightMargin uninstall
record reported the approved name/version, and the installed executable and
uninstaller carried FlightMargin version metadata.

An installed FlightMargin launch against an isolated legacy-data fixture copied
the database and preferences, skipped the legacy log, preserved the source
directory byte-for-byte, and started the packaged sidecar/process tree. Normal
silent uninstall removed the executable, uninstaller, Start Menu shortcut, and
uninstall record while preserving a database fixture. The local test install
and its duplicate test-data directory were removed afterward; the real legacy
internal installation and data were not changed.

## Deferred work

- No GitHub repository rename or visibility change.
- No public release, Git tag, package publication, or GitHub Release.
- No signing integration or auto-update.
- No history rewrite or production service migration.
