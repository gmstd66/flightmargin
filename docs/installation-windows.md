# FlightMargin installation on Windows

Status: `0.3.0-beta.1` is prepared locally but not published.

The validated target is Windows 11 x64 with Microsoft Edge WebView2, an
installed Codex CLI, and an authenticated Codex session available to that CLI.
Windows 10 is not yet a supported claim.

After a public beta is separately approved, download the matching
`FlightMargin-<version>-Windows-x64.exe` and `.sha256` files from the official
GitHub prerelease, verify the checksum, fully Quit any running FlightMargin or
legacy internal build from its tray, and run the current-user installer.

The renamed beta uses bundle identifier `io.github.gmstd66.flightmargin` and
may install alongside the internal 0.2.0 application. Its first launch copies
history and preferences from `%LOCALAPPDATA%\Codex Quota Monitor` to
`%LOCALAPPDATA%\FlightMargin` only if the new directory is absent. The legacy
directory is preserved. The internal app can then be explicitly uninstalled
without removing migrated user data.

The beta is unsigned and has no auto-update. Do not disable Defender or
SmartScreen; do not install artifacts from an unapproved location. See
[Windows public beta guide](windows-public-beta.md) for use and troubleshooting
and [Privacy](privacy.md) for stored data.
