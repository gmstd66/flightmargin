# Native Desktop Prototype Implementation

Status: the Windows desktop shell is internal/beta ready after native validation. It remains unsigned and is not a public or signed distribution.

Milestone 6.18 prepares the current 0.2.0 build for owner GUI/product review.
It records the present dashboard, diagnostics, and tray behavior in
`docs/gui-product-review.md`; it does not authorize a public release, license
selection, signing implementation, or Tauri auto-update.

Milestone 6.19 reduces the Windows shell from 1200×850 (minimum 900×650) to
600×450 (minimum 560×400). The dashboard uses a compact four-column,
three-row snap grid with pointer-handle drag-swap placement, bounded responsive
card dimensions, visibility controls, and reset. Layout schema 3 replaces
incompatible schema-2 geometry while preserving unrelated desktop preferences.
Preferences are stored in `%LOCALAPPDATA%\Codex Quota Monitor\desktop-preferences.json`.
Remaining quota is neutral above 25%, warning at 25% or less, and critical red
at 10% or less. The PyInstaller sidecar is built with `--noconsole` on Windows,
and the release Tauri entry point uses the Windows GUI subsystem. Dashboard
asset revisions prevent WebView2 from retaining an obsolete stacked layout.
The single Windows tray icon is retained. After each existing collector sample,
its tooltip shows `Weekly remaining: xx%` and `5-hour remaining: xx%`; the
Settings tray preference returns the tooltip to the neutral monitoring label.
Windows notification-area icons are too small for two readable percentage
strings, so no text is rendered into the icon itself.

## Project layout

```text
app/desktop.py                         Python sidecar entry point
app/core/config.py                     desktop data-root selection
app/core/environment.py                cross-platform Codex discovery
desktop/frontend/                      short native-shell loading page only
desktop/scripts/prepare-tauri-config.py  derives manifests from app.version
desktop/scripts/build-sidecar.py       native PyInstaller sidecar builder
desktop/src-tauri/                     Tauri 2 shell, permissions, templates
```

The dashboard itself is not copied. The Tauri window initially loads the small local loading page and then navigates to the existing FastAPI dashboard after the sidecar is healthy. Templates, CSS, JavaScript, `/api/*`, and `/static/*` therefore remain owned by the Python package.

## Backend lifecycle and network boundary

`app.desktop` enables `CODEX_QUOTA_DESKTOP=1`, forces `CODEX_QUOTA_HOST=127.0.0.1`, and creates a listening socket at `127.0.0.1:0`. It passes that already-bound socket to Uvicorn and writes exactly one line to stdout:

```text
CODEX_QUOTA_DESKTOP_PORT=<port>
```

The operating system selects the port. This avoids a fixed-port conflict and avoids the parent-reserves-then-releases race. The Tauri shell parses only that readiness line, polls `/api/health` for up to 15 seconds, then navigates to the dashboard. It retains the child handle and kills it when the desktop process exits. Sidecar stdout/stderr is logged by the shell; authentication material and quota payloads must not be added to logs.

The prototype has no API token by approved design. The service is loopback-only; this is not a security boundary against other same-user local processes. Reconsider a per-launch token before adding mutating APIs or broadening the distribution threat model.

## Data and Codex discovery

Desktop mode stores mutable data independently of a source checkout or Linux production installation:

| Platform | Default data root |
| --- | --- |
| Windows | `%LOCALAPPDATA%\Codex Quota Monitor` |
| macOS | `~/Library/Application Support/Codex Quota Monitor` |
| Linux | `$XDG_DATA_HOME/codex-quota-monitor` or `~/.local/share/codex-quota-monitor` |

`CODEX_QUOTA_DATA_DIR` still overrides this path. `quota.db` is stored beneath it unless `CODEX_QUOTA_DB` is explicitly set.

Codex remains user-installed and is never bundled. Discovery is: `CODEX_BIN`, `PATH` (`codex` and `codex.exe` on Windows), then the documented standalone location `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin\codex.exe` on Windows or `~/.local/bin/codex` on macOS/Linux. The existing doctor and collector error states remain the diagnostic path when Codex is missing or unauthenticated.

## Building locally

Install PyInstaller only in a disposable or dedicated build environment, never into the production virtual environment:

```bash
python -m pip install pyinstaller
python desktop/scripts/build-sidecar.py
```

The script creates a native one-file executable under `desktop/src-tauri/binaries/` using the Tauri target-triple naming convention. It collects the Python app, FastAPI dependencies, templates, and static files. Build each target on that target OS; a Linux sidecar is not a Windows executable.

Generate Tauri manifests before Tauri development or builds:

```bash
cd desktop
npm install
npm run prepare
npm run tauri:dev
# or: npm run tauri:build
```

`prepare` writes ignored `Cargo.toml` and `tauri.conf.json` files from committed templates, substituting the canonical `app.version.__version__`. This is the only desktop-manifest version flow; do not hand-edit generated files. The matching sidecar must exist under `src-tauri/binaries/` before packaging.

## Windows validation checklist

Perform this checklist on a real Windows machine; do not treat Linux validation as evidence for any item below.

## Windows-native validation record

Milestone 6.16C was validated on Windows 11 Pro 10.0.26200 x64 with Python 3.14.3, PyInstaller 6.22.3, Node 24.19.0, npm 11.17.0, Rust/Cargo 1.98.1, Visual Studio Build Tools 2022 (MSVC 19.44.35229), Windows SDK 10.0.26100.0, and WebView2 Runtime 153.0.4234.48.

- The native PyInstaller build produced `codex-quota-backend-x86_64-pc-windows-msvc.exe`. It started independently, announced an OS-selected `127.0.0.1` port, served the dashboard, CSS, JavaScript, health endpoint, and authenticated quota endpoint, and placed SQLite under `%LOCALAPPDATA%\Codex Quota Monitor` rather than beside the executable.
- The native Tauri build produced unsigned MSI and NSIS artifacts at version 0.2.0. The NSIS artifact installed per-user and its installed application passed the same sidecar, dashboard, quota, persistence, restart, and shutdown checks.
- On Windows, Uvicorn must receive the already-bound loopback socket through `Server.run(sockets=[listener])`; configuring it with `fd=` causes Uvicorn to attempt an unsupported `AF_UNIX` path. The socket-list form preserves the dynamic-port race protection.
- The Tauri shell resolves the user-installed Codex CLI through PATH; the validated installation used the npm `codex.cmd` wrapper. `CODEX_BIN` override also worked. Isolated missing-Codex and missing-auth tests kept the sidecar running and surfaced the collector diagnostic through `/api/health` and the dashboard's controlled 503 response until a sample became available.
- A one-file PyInstaller sidecar has a launcher and payload process on Windows. Explicit tray **Quit** uses `taskkill /T /F` for the sidecar tree. Closing the dashboard hides it to the tray so monitoring continues; **Open** restores it. The official Tauri single-instance and autostart plugins prevent duplicate collectors and provide an opt-in **Start at login** tray-menu setting.
- If the sidecar cannot start, the Tauri loading page remains open and displays a startup error instead of panicking. The application can then be closed normally.
- The artifacts are unsigned internal-test builds. Microsoft Defender real-time protection remained enabled and no detection was observed. The NSIS install was silent, so interactive SmartScreen behavior was not observed.

1. Install Rust stable, Microsoft C++ Build Tools, Node.js LTS, and the Tauri prerequisites/WebView2 runtime.
2. Install Python and PyInstaller in a dedicated build environment; run `python desktop/scripts/build-sidecar.py` and confirm `codex-quota-backend-x86_64-pc-windows-msvc.exe` is created.
3. Run `npm install`, `npm run prepare`, and `npm run tauri:build` from `desktop/`; inspect the unsigned internal installer only, without publishing it.
4. Launch the installed app and confirm the Python sidecar reports an ephemeral loopback port, `/api/health` responds, and the existing dashboard renders with CSS/JS.
5. Verify discovery through PATH and `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin\codex.exe`; verify `CODEX_BIN` overrides either path.
6. Using a pre-authenticated user Codex installation, verify quota collection; verify missing or expired authentication produces a useful diagnostic while historical data remains visible.
7. Confirm `%LOCALAPPDATA%\Codex Quota Monitor\quota.db` is created, survives restart/upgrade, and is distinct from production or development data.
8. Confirm no firewall prompt or externally reachable listener results from loopback-only binding.
9. Confirm window close, explicit Quit, and backend crash behavior leave no orphan sidecar; implement/test tray/background behavior before claiming it supported.
10. Record unsigned SmartScreen behavior. Do not sign, tag, publish, or enable auto-update without a separate release/security approval.

## Current limits

- Tray lifecycle, single-instance handling, opt-in start-at-login, and bounded local desktop logging are implemented for the Windows beta. An unexpected sidecar exit presents a controlled diagnostic; reopening the application starts a fresh sidecar.
- The primary internal beta installer is current-user NSIS. It preserves `%LOCALAPPDATA%\Codex Quota Monitor` on ordinary uninstall and upgrade. MSI output is no longer a primary beta path.
- Shell logs are `%LOCALAPPDATA%\Codex Quota Monitor\logs\desktop.log`, rotate at 1 MB, and keep one prior file. They must never contain credentials, authentication-file content, or quota payloads.
- Auto-update, native notifications, signed/public distribution, and broad Windows compatibility validation remain pending.
- Linux desktop shell compilation remains unverified.
- Signing and release distribution remain unapproved.
- No desktop installer or release artifact is committed, published, or signed. Local unsigned validation artifacts are development-only and must not be published.
