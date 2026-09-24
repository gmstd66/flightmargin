# Native Desktop Feasibility — Milestone 6.16

Status: architecture study complete. Tauri is the recommended desktop shell, but no framework or desktop deployment implementation is approved yet. A Windows test machine is required before a supported desktop release.

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

This is a recommendation, not an implementation authorization. Adding Tauri, Rust, a Python freezer, supported desktop platforms, or a desktop distribution model crosses the repository's architecture/support decision gate.

## What was verified and what was not

Verified on the Linux development host:

- The existing packaged wheel starts a FastAPI server, reads Codex quota through the installed authenticated CLI, serves the dashboard/static assets, and stores SQLite data in an isolated directory; the release check already validates this on an unreserved development port.
- The dashboard uses relative `/api/*` and `/static/*` URLs and polls existing API endpoints every 15 seconds. It can therefore load almost unchanged from a loopback FastAPI origin.
- Codex CLI 0.153.2 is installed at `/usr/bin/codex` and works with the current stdio adapter.
- Node/npm are present, but Rust/Cargo and Linux WebKit build prerequisites are absent. No Tauri scaffold or binary was created, and no desktop shell was built on this host.

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
3. choose a loopback port, start `codex-quota serve`, and wait for `/api/health` with a bounded timeout;
4. create/load the webview only after health succeeds; show a diagnostic window if it fails;
5. keep the sidecar running when the main window is hidden to tray;
6. terminate the child process on explicit Quit and use a bounded restart/backoff policy for unexpected crashes; and
7. capture sidecar stdout/stderr into the desktop log directory without recording credentials or quota payloads.

The collector already catches individual Codex failures and continues its 60-second loop. Desktop process supervision should restart only a crashed backend process, not restart it for an ordinary Codex/authentication error.

### FastAPI and communication

Keep FastAPI in the initial desktop architecture. It preserves the dashboard exactly, keeps browser/webview development simple, and already separates polling from Codex collection.

Bind only to `127.0.0.1`, never `0.0.0.0`, in desktop mode. Avoid a fixed port: it creates conflicts and makes accidental local discovery easier. The sidecar should report its selected port/readiness to Tauri via a constrained readiness file or a structured stdout line; implement bounded retries because reserving a port in Tauri and releasing it before Python binds has an unavoidable race.

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

An unsigned internal build can be distributed to trusted testers but may display SmartScreen warnings. A public release requires Authenticode code signing; reputation warnings may persist initially even with a certificate. [Tauri's Windows signing guidance](https://tauri.app/distribute/sign/windows/) describes this distinction. Tauri's updater requires signed update artifacts, so defer auto-update and GitHub Release distribution until the signing/release decision is approved. See the [Tauri updater](https://v2.tauri.app/plugin/updater/).

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

## Milestone 6.16B proposal

After explicit architecture approval, implement a Windows-only experimental desktop build:

1. add a `desktop/` Tauri 2 workspace plus build documentation, with no production installer changes;
2. add a native Windows PyInstaller sidecar build that packages the wheel/resources;
3. add desktop configuration/path and Codex-discovery tests, preserving `CODEX_BIN` override;
4. implement loopback startup readiness, health timeout, child cleanup, and desktop log paths;
5. load the existing dashboard from the sidecar endpoint;
6. add single-instance and basic tray show/quit behavior; and
7. validate on a real Windows machine using existing authenticated Codex, isolated `%LOCALAPPDATA%` test data, and an unsigned internal installer.

Do not add autostart, auto-update, notifications, macOS/Linux installers, a local API token, or bundled Codex in 6.16B unless separately approved.

## Decisions required before 6.16B

1. Approve Tauri 2 + PyInstaller sidecar + loopback FastAPI as the Windows-first experimental architecture.
2. Approve Windows as the first supported desktop platform and provide a Windows build/test environment.
3. Decide whether the initial desktop loopback API needs a per-launch session token, based on the intended local threat model.
4. Confirm that unsigned internal installers are acceptable for the experiment; public signing, updates, GitHub Releases, and macOS notarization remain separate future gates.
