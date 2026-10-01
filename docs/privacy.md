# Privacy and local data

FlightMargin is local-first and implements no telemetry or analytics.

## Windows

The desktop application stores these files beneath
`%LOCALAPPDATA%\FlightMargin`:

- `quota.db`: locally collected quota history;
- `desktop-preferences.json`: panel and tray preferences;
- `logs\`: bounded local diagnostics;
- `mobile-relay.json`: non-secret opt-in/sync state;
- `mobile-relay-host.json`: host UUID and a current-user DPAPI-protected relay
  credential, created only after Mobile Relay is enabled.

At the first renamed launch, FlightMargin copies `quota.db` and
`desktop-preferences.json` from `%LOCALAPPDATA%\Codex Quota Monitor` only when
the new directory does not exist. It does not move or delete the legacy
directory and does not migrate old logs or caches. Repeated launches do not
overwrite new data.

The Tauri shell and packaged FastAPI sidecar communicate over an ephemeral
`127.0.0.1` port. The log rotates at 1 MB and retains one prior file.

## Linux

Source checkouts continue to use their local `data/` directory. New installed
user execution uses `$XDG_DATA_HOME/flightmargin` or
`~/.local/share/flightmargin`. If the new location is absent, persistent files
from the legacy `codex-quota-monitor` directory are copied once and the legacy
directory is preserved. Explicit `CODEX_QUOTA_DATA_DIR` and `CODEX_QUOTA_DB`
values are never migrated automatically.

Systemd diagnostics normally remain in the journal or process output. The
browser service has no application-level authentication and must remain on
localhost or a trusted private network.

When Mobile Relay is enabled on Linux, `mobile-relay-host.json` contains the
dedicated relay host token and is stored with mode `0600` under the normal
FlightMargin data directory. The containing directory is restricted to `0700`
when FlightMargin creates it. Treat this file as a secret. The token is
independently revocable and is unrelated to Codex/OpenAI authentication.

## Codex authentication and network behavior

FlightMargin discovers and runs the user's existing Codex CLI. Codex manages
its own authentication. FlightMargin does not ask for, manage, store, or
transmit OpenAI passwords, API tokens, API keys, or `auth.json` contents.

With Mobile Relay disabled (the default), FlightMargin contacts no project-
operated service. When the user opts in, it sends only the latest normalized
quota payload documented in `docs/mobile-relay-design.md` to the configured
relay over verified HTTPS. It does not send Codex credentials, prompts,
transcripts, source code, agent output, local history, usernames, or filesystem
paths. Pairing secrets are held only for the active five-minute UI session and
are not persisted locally. Relay errors shown to the UI are sanitized.

Codex CLI communication with OpenAI remains subject to Codex/OpenAI behavior
and policies outside this project's control.

## Uninstall

A normal Windows uninstall preserves the FlightMargin data directory. Users
who want complete removal can delete it after quitting and uninstalling. The
legacy internal directory is likewise preserved unless the user explicitly
removes it. Neither action removes Codex CLI or its authentication.
