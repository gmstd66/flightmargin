# Linux and Windows functional parity

Milestone 6.20B treats the Windows product experience as the user-facing
reference while retaining native platform mechanics. Both editions run the
same Python collector, normalization, metrics, API, SQLite store, Jinja
templates, CSS, and JavaScript. Tauri is a Windows shell around that shared
application; it is not a second quota implementation.

## Feature matrix

| Area | Status | Linux/browser | Windows desktop |
| --- | --- | --- | --- |
| 5-hour and weekly quota | Shared | Same normalized fields and cards | Same |
| Reset countdowns | Shared | Same API metrics and formatter | Same |
| Weekly Pace and projected exhaustion | Shared | `app.core.metrics` | Same |
| Full Resets | Shared | Same collected/stored field | Same |
| Purchased Credits | Shared | Exact API value; unavailable and zero are explicit | Same value also feeds its tray icon |
| Account/plan | Shared | Same collected/stored field | Same |
| Weekly History | Shared | Same SQLite query, API, canvas graph, and seven-day view | Same |
| Quota states | Shared | API supplies normal, warning, or critical | Same |
| Panel visibility | Shared | Browser Settings; persisted locally | Native Settings; same API/file |
| About/diagnostics | Behavior differs | Browser Settings/About | Native Settings/About window |
| Startup integration | Not applicable | systemd enablement | Start-at-login integration |
| Tray indicators | Windows only | No native tray | App, weekly, 5-hour, and Credits icons |
| Packaging | Behavior differs | Native Python/venv and systemd | PyInstaller sidecar, Tauri, NSIS |
| Service diagnostics | Linux only | CLI doctor/status and systemd journal | Desktop logs and GUI diagnostics |

## Canonical data and calculations

- `app.adapters.codex_stdio.CodexAppServer` calls the structured
  `account/rateLimits/read` JSON-RPC method on both platforms. Transcript
  scraping is not used.
- `app.core.quota.normalize_rate_limits` identifies windows by duration and
  normalizes reset, plan, credits, spend-control, and reached-limit fields.
- `app.core.metrics.window_metrics` owns remaining percentage, countdown,
  pace, and projected-exhaustion calculations.
- `app.core.metrics.quota_state` owns the semantic thresholds: normal above
  25% remaining, warning at or below 25%, and critical at or below 10%.
- The API adds each window's semantic `state`; existing fields remain intact.

## Dashboard parity

The shared default order is 5-hour and Weekly quota, Weekly Pace, Full Resets,
Account, then Weekly History. All panels are visible by default. The fixed,
compact grid, state colors, five Y-axis ticks, compact 8 px Y-axis labels, and
remaining-height History behavior come from the same assets on both platforms.

Normal browser sizes use the compact multi-column layout and allow History to
absorb remaining height. Viewports smaller than the native Windows minimum can
reflow to two columns and document scrolling rather than clipping content.

Loading, collection-error, manual-refresh, and unavailable-data states are
shared. A temporary collector failure reports that an older sample is shown
without exposing raw exception details in the dashboard.

## Data and history

Both editions use the same `quota_samples` schema and preserve:

- capture time;
- 5-hour and weekly used percentages and reset timestamps;
- plan type;
- full-reset count;
- exact purchased-credit balance;
- spend-control and reached-limit state.

The History API supports 1–720 hours and the dashboard requests 168 hours.
There is currently no automatic sample-deletion policy. Missing optional fields
remain `null`; the dashboard renders them as unavailable rather than retaining
stale values.

## Configuration and diagnostics

Panel visibility is a useful cross-platform preference and uses the existing
local preference file. Tray and start-at-login controls are hidden in a normal
browser because they are Windows-only. Linux startup remains a systemd concern.

The shared About API reports the canonical app version, Beta status, detected
Codex CLI version, OS, architecture, data location, and log location. Linux
home paths are abbreviated and Linux logs are described as systemd journal or
process output. Diagnostics remain allowlisted and omit credentials, account
identity, and quota values.

## Intentional platform differences

Windows uses a native shell, native Settings placement, tray lifecycle,
single-instance activation, start-at-login, file logs, PyInstaller, and NSIS.
Linux remains browser/headless, uses systemd and journal/process logging, and is
installed as Python. No Tauri, native tray, or Windows startup emulation is
required for Linux parity.

## Validation status

6.20B native Linux validation completed on Ubuntu 24.04.5 LTS x86_64 with
Python 3.12.3 and Codex CLI 0.153.2. An isolated development venv and SQLite
data directory ran the real authenticated `account/rateLimits/read` collector
on loopback-only temporary ports. Contract checks confirmed both quota
windows, reset timestamps, Weekly Pace and exhaustion calculation, reset
credits, account metadata, purchased credits, history, dashboard assets,
browser Settings/About, refresh, panel preferences, and threshold states
without recording account or quota values in this document.

The missing-Codex path was simulated only through `CODEX_BIN`; it produced the
controlled public message, no stale quota sample, a renderable dashboard, and
available diagnostics. A temporary per-user
`codex-quota-test-parity.service` used only the development checkout/venv,
temporary SQLite data, and loopback port. Its install/start, collection,
SQLite writes, restart, clean stop with no remaining children, start-again,
journal inspection, and cleanup all passed. Production was inspected
read-only afterward and remained active and isolated.

The final isolated suite passed 108 Python tests; JavaScript syntax and API
compatibility checks passed. Baseline (not an optimization target) was three
processes, about 175 MB combined RSS, about 0.10% idle CPU for the server over
a ten-second interval, a 16 KB temporary database, and about 3.3 KB of test
service journal output.
