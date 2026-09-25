# Windows beta checklist

Codex Quota Monitor desktop builds are unsigned internal/beta builds. They are
not public-release artifacts and do not provide auto-update.

## User data and logs

- Application data and SQLite history: `%LOCALAPPDATA%\Codex Quota Monitor\quota.db`
- Desktop-shell logs: `%LOCALAPPDATA%\Codex Quota Monitor\logs\desktop.log`
- The log is rotated at 1 MB and retains one previous file. Do not add tokens,
  auth-file content, or quota payloads to these logs.
- Normal uninstalls preserve this directory. An upgrade must preserve it too.
- `desktop-preferences.json` stores dashboard panel visibility and the
  tray-indicator choice. Dashboard geometry is fixed and is not persisted.

## Repeatable beta validation

1. Install the current-user NSIS installer and verify its Start menu entry.
2. Launch the application. Confirm the loading state, dashboard, CSS/JS, and
   authenticated quota read all work with the user's existing Codex CLI.
   At the 600×450 default, confirm all six panels and the compact history graph
   are visible without scrollbars. In Settings, hide several panels and confirm
   the remaining cards reflow; use **Show all panels** to restore the complete
   fixed dashboard.
3. Close the dashboard window. Confirm monitoring remains available from the
   tray; verify the blue Weekly, purple 5-hour, and green Credits numeric
   indicators update without duplicates. Credits must be floored to a whole
   number, use `999+` above 999, and retain the exact whole balance in its
   tooltip. Use **Open** to restore the dashboard and **Quit** to stop the
   sidecar tree.
   Confirm `%LOCALAPPDATA%\Codex Quota Monitor\logs\desktop.log` records the
   loaded tray preference and each icon's creation, with any failure isolated
   to the named indicator.
4. Toggle **Start at login** from the tray menu, verify it is disabled by
   default, and verify it is removed when toggled off or when the app is
   uninstalled.
5. Start the executable a second time. Confirm it focuses the existing window
   and does not create another tray icon, sidecar, or SQLite writer.
6. Restart after a quota sample exists. Confirm history survives and the new
   sidecar uses a new ephemeral `127.0.0.1` port.
7. Install a newer internal build over the existing installation. Confirm the
   Start menu has one entry, application files update, and history/preferences
   remain intact. Uninstall and confirm user data remains intact.
8. In an isolated environment, test missing Codex and unavailable Codex
   authentication. The app must show a useful controlled diagnostic and stay
   exit-safe; do not alter the user's real authentication.
9. Record any interactive SmartScreen prompt and Defender observation. Do not
   disable either product or add exclusions to complete this checklist.
10. Launch from both the Start menu and installed executable. The release shell
    and its windowless sidecar/Codex subprocess chain must not display a console.
11. Open Settings **About** and confirm the canonical app version and detected
    Codex CLI version. Expand **Technical details**, copy diagnostics, and
    confirm the text contains only app/CLI versions, OS/architecture, and
    `%LOCALAPPDATA%` application-data/log paths. It must not contain account,
    quota, authentication, credential, or Windows-user details.

## Distribution gate

Before public distribution, obtain a code-signing certificate, sign the
desktop executable and NSIS installer with a trusted timestamp, and repeat
the SmartScreen reputation check. Tauri's signing guidance and Microsoft's
SignTool documentation are the implementation references. Certificate choice,
annual cost, hardware/cloud key custody, and any Microsoft Store path require
human approval. Microsoft Store packaging remains a future distribution
alternative, not part of this beta workflow.
