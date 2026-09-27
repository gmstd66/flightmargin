# FlightMargin 0.3.0-beta.1

FlightMargin 0.3.0-beta.1 is the first public beta of a lightweight,
local-first monitor focused on OpenAI Codex usage limits. It supports a Windows
11 x64 desktop application and Linux/headless/browser use.

## Highlights

- 5-hour and Weekly usage limits with reset information
- Weekly Pace and projected exhaustion
- purchased Credits when reported by Codex
- local SQLite history and a seven-day history view
- Windows tray indicators for Weekly, 5-hour, and Credits values
- Settings, About metadata, and sanitized diagnostics
- local-first operation with no FlightMargin telemetry

FlightMargin requires an existing installed and authenticated Codex CLI. Codex
is not bundled, and FlightMargin does not ask for or store OpenAI credentials.

## Windows download safety

The Beta 1 Windows installer is intentionally unsigned. Windows may show
Unknown Publisher or Microsoft Defender SmartScreen warnings. Download the
installer and its `.sha256` file only from the official GitHub Release, then
follow the [PowerShell verification instructions](installation-windows.md)
before deciding whether to run it. Do not disable Windows security controls.

## Beta limitations

- Windows 11 x64 is the validated desktop target; Windows 10 is not claimed.
- There is no automatic updater.
- The browser service has no application-level authentication and should stay
  on localhost or a trusted private network.
- This is beta software; interfaces and compatibility behavior may change.

FlightMargin is an unofficial community tool and is not affiliated with or
endorsed by OpenAI.

Report problems through the [issue tracker](https://github.com/gmstd66/flightmargin/issues).
Security reports should follow [SECURITY.md](../SECURITY.md), and local data
handling is described in the [privacy documentation](privacy.md).
