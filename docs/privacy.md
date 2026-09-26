# Privacy and local data

Codex Quota Monitor is local-first and currently implements no remote
telemetry.

## Data stored on Windows

The desktop application stores the following beneath
`%LOCALAPPDATA%\Codex Quota Monitor`:

- `quota.db`: locally collected quota history;
- `desktop-preferences.json`: panel visibility and desktop preferences;
- `logs\`: bounded diagnostic logs.

Logs rotate locally and must not contain credentials, authentication-file
contents, account identity, or raw quota payloads. **Copy diagnostics** exposes
only allowlisted application, Codex CLI, operating-system, architecture, and
friendly data/log-path information.

## Data stored on Linux

Linux stores the same SQLite history and panel-visibility preference in its
configured data directory. Source checkouts default to `data/`; installed-user
execution follows `XDG_DATA_HOME` or `~/.local/share/codex-quota-monitor`.
Service diagnostics normally remain in the systemd journal or the server
process output rather than the Windows desktop log directory.

## Codex authentication

Codex Quota Monitor discovers and runs the user's existing Codex CLI. Codex
itself manages its authentication. This application does not ask for, manage,
store, or transmit the user's OpenAI password, API token, or `auth.json`
contents.

## Network behavior

The Windows shell and its packaged FastAPI sidecar communicate over an
ephemeral `127.0.0.1` port. The application contacts no project-operated
telemetry or analytics service. Codex CLI communication with OpenAI remains
subject to Codex/OpenAI behavior and policies outside this project's control.

The Linux service binds to its configured address. It has no application-level
authentication and should remain on localhost or a trusted private network.

## Uninstall and removal

A normal Windows uninstall preserves `%LOCALAPPDATA%\Codex Quota Monitor` so
history and preferences survive upgrades. Users who want complete local-data
removal can delete that directory after quitting and uninstalling the app.
