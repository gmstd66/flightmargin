# FlightMargin installation on Windows

Status: `0.3.0-beta.1` is a release candidate and is not published.

The validated target is Windows 11 x64 with Microsoft Edge WebView2, an
installed Codex CLI, and an authenticated Codex session available to that CLI.
Windows 10 is not yet a supported claim.

After a public beta is separately approved, download both files from the
official FlightMargin GitHub Release:

```text
FlightMargin-0.3.0-beta.1-Windows-x64.exe
FlightMargin-0.3.0-beta.1-Windows-x64.exe.sha256
```

From PowerShell in the download directory, calculate the installer checksum:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath .\FlightMargin-0.3.0-beta.1-Windows-x64.exe
Get-Content -LiteralPath .\FlightMargin-0.3.0-beta.1-Windows-x64.exe.sha256
```

Compare the 64-character SHA-256 value reported by `Get-FileHash` with the
value at the start of the published `.sha256` file. They must match exactly,
ignoring letter case. If they do not match, do not run the installer; delete
both downloads and report the mismatch through the
[public issue tracker](https://github.com/gmstd66/flightmargin/issues).

Fully Quit any running FlightMargin or legacy internal build from its tray,
then run the current-user installer.

The renamed beta uses bundle identifier `io.github.gmstd66.flightmargin` and
may install alongside the internal 0.2.0 application. Its first launch copies
history and preferences from `%LOCALAPPDATA%\Codex Quota Monitor` to
`%LOCALAPPDATA%\FlightMargin` only if the new directory is absent. The legacy
directory is preserved. The internal app can then be explicitly uninstalled
without removing migrated user data.

FlightMargin Beta 1 is intentionally unsigned. Windows may identify the
installer as **Unknown publisher** or show a **Microsoft Defender SmartScreen**
warning. This is expected for Beta 1, but a warning is not proof that a file is
safe: download only from the official GitHub Release and verify SHA-256 before
deciding whether to continue. Do not disable Defender or SmartScreen and do
not bypass a warning blindly.

The source and the GitHub Actions workflow used to build the candidate are
public at [gmstd66/flightmargin](https://github.com/gmstd66/flightmargin).
Beta 1 has no auto-update. See
[Windows public beta guide](windows-public-beta.md) for use and troubleshooting
and [Privacy](privacy.md) for stored data.
