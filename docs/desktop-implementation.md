# Native Desktop Prototype Implementation

Status: the first desktop prototype is implemented in the development branch. The Python sidecar and its loopback dashboard were validated on Linux. The Tauri project is configured but has not been compiled on this host because Rust/Cargo and Linux WebKit development prerequisites are absent. Windows remains the first intended desktop target and requires native validation before any supported distribution.

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

- Tray, single-instance, autostart, auto-update, native notifications, and restart/backoff policy are intentionally not implemented in this prototype.
- The Tauri project has not been Rust-compiled on Linux or Windows yet.
- The Windows executable discovery path is tested as path-selection logic only, not against Windows Codex.
- No desktop installer or release artifact is committed, published, signed, or installed.
