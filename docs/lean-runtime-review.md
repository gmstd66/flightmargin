# Lean runtime review

Milestone 6.20C reviewed current HEAD `0284459` before changes and the retained
optimized build on Windows 11 x64 on 2026-09-26. Sizes use binary MiB. Runtime
measurements used a clean data directory, the same authenticated Codex
installation, a stabilized visible dashboard, and a 32-logical-processor host.
No production Linux resource was accessed.

## Result

The application is **acceptable with known unavoidable runtime overhead** for
a public beta. Its owned installer is small (16.84 MiB), local persistent data
grows slowly, idle activity is quiet, and retained changes remove measurable
packaging and launcher waste. Python, the persistent Codex app-server, and the
Microsoft WebView2 multi-process runtime remain the principal costs.

## Before and after

| Windows metric | Baseline | Final | Change |
| --- | ---: | ---: | ---: |
| NSIS installer | 19,441,715 B (18.541 MiB) | 17,652,778 B (16.835 MiB) | -1,788,937 B (-9.20%) |
| Installed runtime files | 29,089,967 B (27.742 MiB) | 26,700,806 B (25.464 MiB) | -2,389,161 B (-8.21%) |
| Tauri executable | 12,043,264 B (11.485 MiB) | 11,388,416 B (10.861 MiB) | -654,848 B (-5.44%) |
| PyInstaller sidecar | 16,967,455 B (16.181 MiB) | 15,233,142 B (14.527 MiB) | -1,734,313 B (-10.22%) |
| Dashboard templates/static | 37,194 B (36.32 KiB) | unchanged | 0 |
| Tauri startup placeholder | 839 B | unchanged | 0 |
| Source icons | 7,259 B (7.09 KiB) | unchanged | 0 |
| App-owned processes, excluding WebView2 | 7 | 5 | -2 (-28.6%) |
| Microsoft WebView2 processes | 6 | 6 | unchanged |
| Total attributable processes | 13 | 11 | -2 (-15.4%) |
| Child processes below Tauri | 12 | 10 | -2 |
| App-owned RSS, excluding WebView2 | 286.70 MiB | 225.55 MiB | -61.15 MiB (-21.33%) |
| WebView2 RSS | 322.55 MiB | 321.09 MiB | measurement noise |
| Total attributable RSS | 609.25 MiB | 546.64 MiB | -62.61 MiB (-10.28%) |
| App-owned private bytes | 124.00 MiB | 90.23 MiB | -33.77 MiB |
| WebView2 private bytes | 162.99 MiB | 162.20 MiB | measurement noise |
| Idle CPU, one-core equivalent | 0.31% | 0.47% | timer noise; no regression established |
| Idle CPU, machine-normalized | 0.010% | 0.015% | effectively unchanged |
| Launch to visible window | 0.325 s | 0.300 s | -0.025 s (-7.7%) |
| Launch to healthy API | 2.971 s | 2.902 s | -0.069 s (-2.3%) |
| Launch to first valid quota | 2.974 s | 2.907 s | -0.067 s (-2.3%) |
| Idle process writes (20 s) | 37,685 B | 16,720 B | variable WebView2 cache traffic |
| Idle persistent log growth | 0 B | 0 B | unchanged |
| Projected yearly SQLite size | 40.64 MiB plus startup duplicates | 40.64 MiB, no startup duplicate | one row removed per launch |

Installed runtime is the two application executables plus the 79,248-byte
NSIS uninstaller. Mutable database, preferences, and logs are separate. The
system-wide WebView2 installation is not bundled and is not included in size.

RSS is accompanied by private bytes because working-set totals double-count
shared pages. The baseline app-owned set was Tauri, the PyInstaller bootloader
and Python child, `cmd`, console host, Node, and native Codex. The final set is
Tauri, two PyInstaller processes, native Codex, and its console host. WebView2
separately used a browser, crash handler, GPU, network, storage, and renderer
process. This normal platform isolation was not suppressed.

## Footprint sources

- The sidecar is the largest owned component. Its largest compressed members
  are Python 3.14 (2.59 MiB), Pydantic Core (1.81 MiB), OpenSSL crypto (1.77
  MiB), SQLite (0.80 MiB), and the 5.03 MiB Python-module archive. FastAPI,
  Starlette, AnyIO, Uvicorn, Pydantic, Jinja2, and their transitives are needed.
- The Tauri executable is 10.861 MiB. Shell, autostart, single-instance, tray,
  JSON, and URL dependencies all implement approved behavior.
- Dashboard assets exist only in the sidecar. Tauri's 839-byte startup/error
  placeholder is required before loopback health and is not a second dashboard.
- `icon.ico` is the only bundled icon; the 444-byte SVG is a source asset.
- NSIS adds a 79,248-byte uninstaller and compression/container metadata. It
  does not bundle WebView2.
- The 3.52 MiB final PDB, caches, PyInstaller analysis, docs, tests, Node
  dependencies, and source maps are not shipped.
- No fonts, media, stale draggable/resizable code, legacy modal assets, caches,
  documentation, or duplicate dashboard revisions are packaged.

## Dependency audit

Python runtime requirements remain FastAPI, Uvicorn, and Jinja2. Required
transitives include Starlette, Pydantic/Core, AnyIO, Click, h11, MarkupSafe,
annotated/typing helpers, and IDNA. Pytest, Pluggy, Iniconfig, and Pygments are
test-only. PyInstaller/hooks, Altgraph, PEfile, pywin32-ctypes, Setuptools,
Wheel, and Packaging are packaging-only. They are not Linux runtime requirements.

The Windows build environment contained optional PyYAML although it is not a
locked project requirement. Uvicorn needs it only for optional YAML config;
this application constructs `uvicorn.Config` directly. PyYAML and Setuptools
are now excluded from PyInstaller. No required indirect import was removed.

JavaScript has no runtime package dependency; the sole npm package is the
build-only Tauri CLI. Rust dependencies and capabilities match actual use.
Removing a plugin would remove an approved feature.

The unpacked application source is 98,781 bytes and the wheel is 35,408 bytes.
On this build environment, the largest unpacked runtime packages were Pydantic
Core 5.29 MiB, Pydantic 3.82 MiB, AnyIO 1.97 MiB, FastAPI 1.43 MiB, Jinja2
1.25 MiB, Click 0.98 MiB, Uvicorn 0.69 MiB, and Starlette 0.68 MiB.

## Retained optimizations

1. Excluding optional Setuptools and PyYAML reduced the sidecar 1.66 MiB
   (10.22%). Full API/static/About smoke passed against the built sidecar.
2. One release codegen unit, thin LTO, and symbol stripping reduced Tauri by
   639 KiB (5.44%). Normal panic behavior remains; `panic = "abort"` was not used.
3. Recognized official Windows npm shims resolve to packaged native Codex, with
   fallback and exact preservation of explicit `CODEX_BIN`. This removed
   resident `cmd.exe` and Node, saving 61.15 MiB app-owned RSS. Real quota and
   process-tree shutdown passed.
4. The collector waits one interval after lifespan's initial sample. This
   removes the second startup request/row and preserves 60-second cadence.
5. `npm run tauri:build` now uses repository-venv Python for sidecar and
   manifest generation, completes end to end, and still prevents stale assets.

## Rejected or deferred changes

- Removing PyInstaller's broad `app` collection changed size by +1,210 bytes
  (build noise), so it was reverted to preserve indirect-import safety.
- UPX was not enabled. Antivirus/SmartScreen, extraction, and reliability
  tradeoffs are unjustified for a 16.84 MiB unsigned installer.
- One-file PyInstaller was retained. It explains two sidecar processes and
  some startup extraction, but supplies one predictable sidecar and compact
  installation. Onedir would add many files and packaging complexity.
- Persistent Codex was retained. Restarting it each minute would repeat launch
  and discovery work and reduce reliability.
- WebView2 processes were not collapsed; they are Microsoft runtime isolation.
- Frameworks, approved features, and architecture were not replaced.
- Logging was not further reduced: only concise startup/lifecycle/warning/error
  records persisted, and normal refresh/sample activity did not grow the log.

## Polling, network, disk, and logs

Backend sampling is 60 seconds by default (minimum 10). Final DB timestamps
were 61 seconds apart after duration/rounding. The dashboard loads quota/history
once and refreshes those cached loopback endpoints every 15 seconds.
Preferences load on initialization/change; About only when opened. Tray icons
consume the existing sample and do not poll. Health probing is startup-only.

Normal traffic is WebView/browser to loopback FastAPI every 15 seconds, backend
to persistent Codex over stdio every 60 seconds or manual Refresh, and Codex to
its service as required for authenticated quota/account retrieval. There is no
telemetry, analytics, updater, advertising, crash upload, or other application
external request. No duplicate Tauri/tray/backend poller was found.

Final stabilized process writes were 16,720 bytes/20 seconds: 16,584 WebView2
and 136 other app-owned bytes. Neither DB nor log grew. `desktop.log` stayed 571
bytes through a scheduled sample. It rotates on startup at 1,000,000 bytes and
retains one prior file, so normal persistent footprint is about 2 MB maximum
plus any single-session overshoot. Useful errors remain; credentials and quota
values are not logged.

## SQLite growth

The actual schema and index populated at 60-second cadence measured:

| Period | Rows | Database size |
| --- | ---: | ---: |
| 1 day | 1,440 | 131,072 B (128 KiB) |
| 30 days | 43,200 | 3,465,216 B (3.30 MiB) |
| 1 year | 525,600 | 42,610,688 B (40.64 MiB) |

SQLite uses 4 KiB pages, delete journal, and no persistent WAL. There is one
useful captured-time index and no duplicate steady sampling. The API reads at
most 720 hours; the dashboard reads seven days. Retention/VACUUM is unnecessary
for a one-year beta DB. Five years would approach 203 MiB. Automatic deletion
is a user-data retention decision and is deferred for explicit owner approval.

## Linux review

The supplied 6.20B isolated baseline is three processes, about 175 MiB RSS,
about 0.10% idle CPU, a 16 KiB temporary DB, and about 3.3 KiB journal output.
The runtime package is the 35,408-byte wheel plus required dependencies; source
package content is 98,781 bytes.

Commit `11d94cf`, integrated before milestone completion, is the authoritative
native Ubuntu 24.04.5 x86_64 validation: Python 3.12.3, Codex CLI 0.153.2, real
authenticated collection, isolated loopback ports/data, and a temporary
`codex-quota-test-parity.service`. It also verified read-only that production
remained active and isolated. That retained evidence did not record exact venv
bytes or startup-to-health/first-sample timers, so those two values are not
invented here. This Windows host has no WSL/Docker/native Linux runner, and
6.20C did not access production Linux.

No retained packaging/npm optimization executes on Linux. The only shared
change removes one duplicate startup sample; process count, RSS, dependencies,
and 60-second cadence are otherwise unchanged. The final Linux figures remain
three processes, about 175 MiB RSS, about 0.10% idle CPU, 16 KiB initial DB,
about 3.3 KiB temporary journal output, and the same 40.64 MiB/year projection.

## Validation summary

- Required `npm run tauri:build`: passed; sidecar rebuilt and unsigned NSIS
  created without publication.
- Installed NSIS payload: measured after local silent development install.
- Authenticated Windows runtime: dashboard, assets, quota, history,
  preferences, Settings, About, health, and collector all returned HTTP 200.
- Sample cadence, windowless launch, clean shutdown tree, and bounded logs were
  measured directly.
- Full command/test evidence is recorded in project status and the completion
  report.
