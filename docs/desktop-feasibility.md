# Native Desktop Feasibility — Milestone 6.16

Status: the approved Tauri/PyInstaller/loopback prototype is implemented. The Python sidecar is Linux-validated; the Tauri manifests are generated and syntax-validated, but no Tauri shell has been compiled on this Linux host. A real Windows machine is required before any Windows runtime or installer claim.

## Recommendation

Use a **Tauri 2 shell with a bundled Python backend sidecar and loopback-only FastAPI** for the first desktop edition. Preserve the existing dashboard, API, quota normalization, SQLite store, and Codex stdio adapter. Tauri owns the window, tray, autostart preference, single-instance behavior, sidecar lifecycle, and installer; Python owns collection and the existing web application.

```text
Tauri window + tray
        │ starts/stops, health-checks, logs
        ▼
packaged Python sidecar ── 127.0.0.1:<random-port> ── existing FastAPI/dashboard
        │                                                    │
        ├── CODEX_BIN → user-installed Codex CLI             └── /api/*, static UI
        ├── desktop app-data directory → quota.db
        └── existing Codex app-server stdio subprocess
```

This architecture is approved for the internal prototype only. It does not approve a public desktop release, code signing, auto-updates, or a supported cross-platform distribution.

## What was verified and what was not

Verified on the Linux development host:

- The existing packaged wheel starts a FastAPI server, reads Codex quota through the installed authenticated CLI, serves the dashboard/static assets, and stores SQLite data in an isolated directory; the release check already validates this on an unreserved development port.
- The dashboard uses relative `/api/*` and `/static/*` URLs and polls existing API endpoints every 15 seconds. It can therefore load almost unchanged from a loopback FastAPI origin.
- Codex CLI 0.153.2 is installed at `/usr/bin/codex` and works with the current stdio adapter.
- A PyInstaller-built Linux sidecar selected OS port `41299`, served `/api/health`, the existing dashboard/CSS/JS, performed an authenticated quota collection, created SQLite only beneath an isolated temporary desktop data root, and stopped cleanly.
- A Tauri 2 workspace now contains the shell, sidecar configuration, strict local CSP, and generated versioned manifests. Node/npm are present, but Rust/Cargo and Linux WebKit build prerequisites are absent, so no Tauri shell was compiled on this host.

Not yet verified:

- Native Windows sidecar spawning, Codex app-server JSON-RPC, installer, tray, autostart, signing, and data paths.
- macOS universal/Apple Silicon packaging, signing, notarization, and Codex discovery.
- Linux desktop bundle/tray behavior across distributions.

## Candidate comparison

| Candidate | Reuse and lifecycle | Size/packaging | Security and maintenance | Assessment |
| --- | --- | --- | --- | --- |
| **A. Tauri + bundled Python sidecar** | Reuses Python core; Tauri manages a frozen backend process, tray, logs, restart, and clean shutdown | Two native artifacts per target; moderate build pipeline complexity | Tauri sidecars and command scopes can be narrowly permitted; native WebView avoids bundling Chromium | Preferred shell/process model |
| **B. Tauri + loopback FastAPI** | Reuses the current HTML/CSS/JS and all API routes nearly unchanged | Same sidecar packaging as A; adds local-port startup handling | Loopback-only server is simple and observable; local same-user access remains a limited threat | Preferred first communication/UI model; combines with A |
| **C. Tauri + IPC/native bridge** | Reuses Python quota/store logic but replaces FastAPI routes and frontend `fetch` calls with a new IPC protocol | No local listener, but substantially more custom protocol/UI work | Smallest local attack surface; little performance benefit for 60-second collection | Future optimization, not first desktop release |
| **PySide6/Qt** | Can reuse Python logic; reusing current UI requires Qt WebEngine or a UI rewrite | Qt/WebEngine makes installers materially larger; Python-native freezing still needed | Strong native APIs/tray, but two UI stacks or a heavyweight web engine | Credible fallback if Tauri/WebView sidecars fail |
| **Electron + Python sidecar** | Very high web UI and process-management reuse | Chromium makes runtime/installers much larger; still packages Python | Mature tray/updater ecosystem, but highest runtime/security-update burden | Technically viable, not justified for this compact local dashboard |

Tauri supports target-specific sidecars and scoped shell permissions; it also has official autostart, single-instance, tray, and updater facilities. See [Tauri sidecars](https://v2.tauri.app/fr/develop/sidecar/), [shell scopes](https://v2.tauri.app/reference/javascript/shell/), and [autostart](https://v2.tauri.app/plugin/autostart/).

## Recommended initial desktop architecture

### Tauri process and backend lifecycle

Build one frozen Python executable per OS/architecture, named and packaged as a Tauri sidecar. Do not ship a virtual environment or require a user Python installation. Tauri should:

1. enforce a single application instance;
2. resolve desktop data/log directories and launch the sidecar with explicit environment variables;
3. start the sidecar, parse its OS-assigned loopback port from constrained stdout, and wait for `/api/health` with a bounded timeout;
4. create/load the webview only after health succeeds; show a diagnostic window if it fails;
5. keep the sidecar running when the main window is hidden to tray;
6. terminate the child process on explicit Quit and use a bounded restart/backoff policy for unexpected crashes; and
7. capture sidecar stdout/stderr into the desktop log directory without recording credentials or quota payloads.

The collector already catches individual Codex failures and continues its 60-second loop. Desktop process supervision should restart only a crashed backend process, not restart it for an ordinary Codex/authentication error.

### FastAPI and communication

Keep FastAPI in the initial desktop architecture. It preserves the dashboard exactly, keeps browser/webview development simple, and already separates polling from Codex collection.

Bind only to `127.0.0.1`, never `0.0.0.0`, in desktop mode. Avoid a fixed port: it creates conflicts and makes accidental local discovery easier. The implemented sidecar binds `127.0.0.1:0` itself, retains that socket for Uvicorn, and reports the selected port through one constrained stdout line. This removes the parent-reserves-then-releases race; Tauri then performs a bounded health poll.

Loopback HTTP is the recommended initial transport. A random loopback port is not remotely reachable and the existing endpoints have low-impact operations (read quota/history and request an immediate refresh). Another local process can still call them. A per-launch session token would improve same-machine multi-user/malware resistance, but requires API middleware and frontend request changes; defer it unless the first desktop threat model includes hostile local processes. Tauri CSP must allow only the selected loopback origin and no remote scripts. See [Tauri CSP guidance](https://v2.tauri.app/security/csp/).

IPC is a later optimization: it eliminates TCP but requires a long-lived Python IPC protocol, a Rust bridge, and changes to the existing web `fetch` UI. It does not materially improve collection latency or reliability.

## Python bundling and application data

### Bundling

For the initial Windows build, use **PyInstaller** to freeze the installed `codex-quota-monitor` package and its FastAPI/templates/static resources into a Python sidecar executable. Build each target on its native OS/architecture and verify the resulting sidecar with the existing wheel checks plus desktop-specific smoke tests.

Do not use a standalone virtual environment for end users: it complicates installation, upgrades, and support. Do not start with the CPython embedded distribution: it is designed for embedders, omits pip, and expects third-party packages to be vendored/managed by the application installer, creating more custom packaging work than a first PyInstaller sidecar. [Python's Windows documentation](https://docs.python.org/3/using/windows.html) describes these embedded-distribution constraints.

Desktop releases must use the canonical `app.version.__version__`. A future desktop build script should generate or validate the Tauri manifest version from that source rather than hand-maintaining a second version number.

### Data paths

The current installed-package default is suitable on Linux through XDG but needs a desktop data-path abstraction before Windows/macOS support:

| OS | Proposed application data root |
| --- | --- |
| Windows | `%LOCALAPPDATA%\\Codex Quota Monitor` |
| macOS | `~/Library/Application Support/Codex Quota Monitor` |
| Linux desktop | `$XDG_DATA_HOME/codex-quota-monitor` or `~/.local/share/codex-quota-monitor` |

Place `quota.db`, sidecar logs, readiness state, and future desktop settings below this root; never place Codex credentials there. A small internal platform-path helper is sufficient initially (`LOCALAPPDATA` on Windows, `Library/Application Support` on macOS, XDG on Linux), so `platformdirs` is not justified yet.

## Codex CLI integration

Use the existing user-installed Codex CLI. Do **not** bundle it:

- It owns the user's authentication, sandboxing, updates, and platform-native behavior.
- Bundling would couple the monitor release cadence to a security-sensitive external executable and create licensing/update/support obligations.
- The current application already accepts `CODEX_BIN`, which is the correct explicit override for a discovered executable.

Discovery order for milestone 6.16B should be:

1. explicit user-configured `CODEX_BIN` path;
2. `PATH` lookup (current behavior);
3. documented standalone-installer location if the file exists: `~/.local/bin/codex` on macOS/Linux and `%LOCALAPPDATA%\\Programs\\OpenAI\\Codex\\bin\\codex.exe` on Windows;
4. a user-selected executable path persisted in desktop settings.

OpenAI documents `CODEX_INSTALL_DIR` with these default installer locations and file-backed credentials under `CODEX_HOME`; Windows-native Codex uses `%USERPROFILE%\\.codex`. See [Codex environment variables](https://learn.chatgpt.com/de-DE/docs/config-file/environment-variables) and [Windows Codex guidance](https://learn.chatgpt.com/docs/windows/windows-app).

If Codex is missing, unauthenticated, or its token expires, the sidecar must remain available, keep historical SQLite data visible, mark live data unavailable, and provide an actionable “Locate Codex” or “Sign in with Codex” diagnostic. The desktop app must not attempt silent login, bundle credentials, or modify authentication state. `codex-quota doctor` is the basis for this status experience.

## Windows-first delivery

Windows should be the first supported desktop OS. It has the highest requested priority, uses native Codex according to OpenAI documentation, and Tauri has Windows installers plus WebView2 support. A Windows developer/build agent must validate:

- `codex.exe` discovery, existing `%USERPROFILE%\\.codex` authentication, and sequential stdio JSON-RPC app-server calls;
- PyInstaller sidecar spawning from the installed Tauri application;
- `%LOCALAPPDATA%` SQLite/log paths and safe upgrade preservation;
- loopback binding, Windows Firewall behavior, tray, autostart, single-instance, and clean child shutdown;
- NSIS/MSI installer behavior and an unsigned internal installation.

Tauri requires Microsoft C++ Build Tools for Windows development and uses Edge WebView2; Tauri documents WebView2 as already present on supported modern Windows versions, with an Evergreen installer fallback. [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/) also note the MSI VBSCRIPT prerequisite.

An unsigned build may display SmartScreen warnings; reputation warnings may persist initially even with a certificate. This feasibility-era signing gate was superseded by the owner decision to release Beta 1 unsigned with required SHA-256 verification and documented warnings. [Tauri's Windows signing guidance](https://tauri.app/distribute/sign/windows/) remains useful post-beta research. Tauri's updater requires signed update artifacts, so auto-update remains deferred. See the [Tauri updater](https://v2.tauri.app/plugin/updater/).

## macOS and Linux path

- macOS: use the same Tauri sidecar/loopback model, `~/Library/Application Support`, and user-installed Codex discovery. Validate x64 and Apple Silicon separately; public distribution requires Apple signing/notarization decisions.
- Linux desktop: keep the existing systemd installer as the supported headless/server path. A desktop bundle can later use the same sidecar and XDG data root, but tray behavior varies by desktop environment and must be tested per package format.
- Tauri's autostart and single-instance facilities list Windows, Linux, and macOS support. On Linux, Tauri documents tray limitations/desktop-environment variation, reinforcing Windows-first scope. See [Tauri tray API](https://v2.tauri.app/reference/javascript/api/namespacetray/).

## Tray and background lifecycle

Tauri is suitable for the intended lifecycle:

```text
optional login launch → one Tauri instance → start healthy Python sidecar
window close → hide window, retain tray + collector
tray click/menu → show dashboard / pause-resume monitoring / quit
quit → stop collector, terminate sidecar, flush logs, exit
```

The first implementation should provide Show, Pause/Resume, Check status, and Quit menu items. Native quota notifications and dynamic tray quota text are later enhancements; keep the existing 15-second dashboard refresh initially.

## Milestone 6.16B implementation status

The approved architecture is now represented in the development branch:

1. `desktop/` contains a Tauri 2 workspace with a native loading page, shell-sidecar lifecycle code, local CSP, and no production installer changes.
2. `desktop/scripts/build-sidecar.py` builds a target-native PyInstaller sidecar with Python modules, templates, static assets, and dependencies.
3. Desktop path selection, Codex discovery, loopback socket allocation, readiness format, and version generation have tests.
4. The sidecar binds an OS-selected loopback socket, reports it through stdout, and supports clean signal shutdown; the Tauri shell holds/kills the child and health-checks before navigation.
5. The shell navigates to the existing dashboard endpoint; no dashboard copy or redesign was added.

The remaining Windows-native work is the checklist in `docs/desktop-implementation.md`, especially a real `tauri build`, installed-app lifecycle, executable discovery, tray/single-instance behavior, and unsigned installer validation.

Do not add autostart, auto-update, notifications, macOS/Linux installers, a local API token, or bundled Codex unless separately approved.

## Remaining gates before Windows-native validation

The architecture, Windows-first scope, no-token internal prototype, and unsigned internal builds are approved. No further architecture decision blocks Windows-native validation. A Windows machine with existing authenticated Codex is required. Signing is deferred post-beta; GitHub Release publication, auto-update, macOS notarization, and any change to the local API threat model remain separate gates.
