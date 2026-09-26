# Windows public beta guide

Status: prepared for review; no public beta has been published.

## Requirements

The currently validated target is:

- Windows 11 x64;
- Microsoft Edge WebView2 Runtime;
- an existing Codex CLI installation discoverable for the current user;
- an existing authenticated Codex/ChatGPT session available to that CLI.

Codex CLI is not bundled. Windows 10 has not been validated and is not yet a
supported claim.

## Install

After launch approval:

1. Open the matching GitHub prerelease.
2. Download the NSIS `-setup.exe` and adjacent `.sha256` file.
3. Verify the installer's SHA-256 value.
4. Fully Quit FlightMargin or an older internal Codex Quota Monitor build from its tray menu.
5. Run the current-user installer and launch the Start menu shortcut.

The first public beta has no automatic updater. Until code signing is active,
Windows may display an unidentified-publisher or SmartScreen warning. Download
only from the project's eventual GitHub Releases page; Defender and SmartScreen
must not be disabled or bypassed globally.

The installer checks for the packaged backend process before copying files. If
it is still running, the installer instructs the user to Quit from the tray and
offers **Retry** instead of proceeding to a raw file-write failure.

## First launch and normal use

The app opens a compact dashboard and begins sampling locally:

- **5-hour quota** and **Weekly quota** show remaining capacity and reset time.
- **Weekly Pace** compares current usage with a sustainable pace.
- **Full Resets** and **Account** show reset-credit, plan, and purchased-credit
  information when Codex supplies it.
- **Weekly History** graphs locally collected history.
- **Refresh** refreshes displayed API data; the backend maintains its own
  collection schedule.
- **Settings** controls panel visibility, tray indicators, and start at login.
- **About** reports versions and offers sanitized **Copy diagnostics** output.

Closing the dashboard keeps monitoring in the tray. The normal app icon offers
Open, Settings, About, start-at-login, and Quit. Optional numeric icons show
Weekly, 5-hour, and purchased Credits values; Windows may place them in the `^`
hidden-icons area.

## Updates

Beta 1 uses manual GitHub prerelease downloads. Auto-update remains deferred.
Before installing a newer beta, fully Quit the running app from its tray menu.
The new installer should preserve history and preferences.

## Uninstall and local data

Uninstall through **Settings > Apps > Installed apps**. Ordinary uninstall
removes the application but preserves:

```text
%LOCALAPPDATA%\FlightMargin
```

That directory contains `quota.db`, preferences, and logs. On the first renamed
launch, persistent data is copied from the legacy internal
`%LOCALAPPDATA%\Codex Quota Monitor` directory only if the new directory is
absent; the legacy directory remains untouched. After uninstalling,
users who also want to erase local history can delete the directory manually.
This does not remove Codex CLI or its authentication.

## Troubleshooting

- **Codex not detected:** install Codex separately, confirm `codex --version`
  works for the same Windows user, then relaunch.
- **Authentication unavailable:** complete the normal Codex authentication flow
  outside this application; do not paste credentials into an issue.
- **Upgrade cannot copy the backend:** fully Quit the app from the system tray,
  return to the installer, and select Retry.
- **Quota icons not visible:** inspect the Windows `^` hidden-icons area and pin
  them manually if desired. Windows controls notification-area placement.
- **Need diagnostic details:** use Settings > About > Technical details > Copy
  diagnostics. Review the text before sharing it.

Issue reports should include reproduction steps and sanitized diagnostics, but
never authentication files, tokens, database contents, account identity, or raw
quota payloads. Security-sensitive reports follow `SECURITY.md`.

## Known first-beta limitations

- unsigned until the approved code-signing path is available;
- manual updates only;
- Windows 11 x64 is the only validated public desktop target;
- user must install and authenticate Codex independently;
- notification icons may be placed in Windows overflow;
- code signing, public repository readiness, and final release approval remain launch gates.

See [Privacy](privacy.md) for actual local-data and network behavior.
