# Windows public beta release checklist

Unchecked gates require current evidence for the exact release commit and
artifact. Beta 1 is intentionally unsigned; signing is not a release gate.

## Product and legal

- [x] FlightMargin public product name approved; ReserveLight retained as fallback
- [x] Selected AGPLv3-or-later terms applied through a reviewed `LICENSE`
- [x] Contribution terms set to the project `AGPL-3.0-or-later` license
- [x] Remote history sanitation complete with atomic leased ref replacement
- [x] Historical author-email/private-infrastructure exposure remediated
- [x] Repository privacy and secret audit rerun against a fresh clone
- [x] Final Linux publication preflight completed against the sanitized checkout
- [x] GitHub private vulnerability reporting enabled
- [x] Repository public at `gmstd66/flightmargin`
- [x] Beta 1 unsigned decision documented; Authenticode/SignPath deferred

## Version and source

- [x] Public version approved as `0.3.0-beta.1`
- [x] Canonical version synchronized across generated manifests
- [x] Exact release-candidate source is identical on `main` and `dev/productization`
- [x] Source corresponding exactly to the candidate binary is public
- [ ] Tag `v0.3.0-beta.1` approved and created (publication gate; not part of 6.21A)

## Candidate build

- [x] GitHub-hosted Windows workflow succeeds for the exact RC commit on `main`
- [x] Python, npm, and Cargo resolved dependency inputs reviewed
- [x] PyInstaller sidecar rebuilt from current dashboard assets locally
- [x] Local Tauri release and NSIS installer build succeeds
- [x] Unsigned installer status and expected Windows warnings documented
- [x] Installer SHA-256 produced and independently checked
- [x] Checksum-verification instructions reviewed

## Native validation

- [x] Isolated Windows 11 x64 installation passes using the CI-built installer
- [x] Existing Codex CLI is detected; Codex is not bundled
- [x] Authenticated health/quota reads pass
- [x] Dashboard and Weekly History render correctly without visible consoles
- [ ] Weekly, 5-hour, and Credits tray indicators pass
- [x] Settings, About, Source Code, Report an Issue, and sanitized diagnostics pass
- [x] Close-to-tray, single-instance, relaunch, and backend cleanup pass
- [x] Transition from the internal 0.2.0 build copies legacy data without loss
- [ ] Running-app installer Retry/Cancel behavior passes
- [x] Uninstall succeeds and documented user-data preservation is accurate
- [x] SmartScreen activation and unsigned/Unknown Publisher status recorded without evasion
- [x] Microsoft Defender result recorded without disabling protection

## Public presentation and release

- [x] README contains no screenshot or private data
- [x] Installation/privacy/troubleshooting docs reviewed for the candidate
- [x] Third-party notice inventory reviewed against exact release lockfiles
- [x] Source Code URL enabled and validated in desktop and browser About
- [x] Report an Issue URL enabled and validated in desktop and browser About
- [x] Sponsorship explicitly deferred; no Sponsor action, `FUNDING.yml`, or donation button
- [x] Release-notes draft completed and internally reviewed
- [ ] GitHub prerelease created only after final human approval
- [ ] Installer and checksum attached only after final human approval

Auto-update and code signing are deliberately excluded from Beta 1. SignPath
may be reconsidered after demonstrated adoption, user feedback, or material
SmartScreen friction. No signing secrets or configuration are currently
required.

## Prior evidence

The 2026-09-27 Linux preflight validated the sanitized checkout's reachable
history and current tree, wheel metadata, both CLI names, authenticated
collection, isolated browser routes, and generated FlightMargin and legacy
systemd units. It made no production change. On the same date, the repository
was renamed to `gmstd66/flightmargin`, made public, given its approved metadata,
and configured for private vulnerability reporting. The Beta 1 tag and GitHub
Release remain separate protected publication gates.

## 6.21A hosted evidence

The first hosted candidate source was
`e071c7864fa32ad43fc587dfcf9db354d45b7f42`. GitHub Actions run
`36345996995` completed successfully and uploaded artifact
`flightmargin-windows-unsigned-e071c7864fa32ad43fc587dfcf9db354d45b7f42`
(artifact ID `10941270569`). It contained exactly:

```text
FlightMargin-0.3.0-beta.1-Windows-x64.exe
FlightMargin-0.3.0-beta.1-Windows-x64.exe.sha256
```

The installer was 17,736,043 bytes. Independent `Get-FileHash -Algorithm
SHA256` produced
`0f8f389784cf99c7ec0946f2629082dc5b8e34ff6e707707a3f8dff615eb09f3`,
which exactly matched the checksum file. Authenticode reported `NotSigned` and
FlightMargin/`0.3.0-beta.1` metadata.

Microsoft Defender Antivirus, antispyware, and real-time protection remained
enabled; a custom scan reported no detection. An exact-hash installer copy with
normal Internet-zone metadata activated the Windows SmartScreen process and
left the installer waiting behind the prompt. The automated session could not
read the prompt text, so the expected Unknown Publisher presentation is also
grounded in the independent `NotSigned` result.

The CI installer passed checkout-local isolated installation, authenticated
collection, Dashboard/History WebView inspection, About/privacy/diagnostic
inspection, both allowlisted external-browser commands without replacing the
webview, single-instance behavior, copy-only legacy migration, process-tree
console inspection, and uninstall with new and legacy user data preserved. A
running-app reinstall remained blocked before copying and left the installed
executable unchanged. Because the agent has no interactive desktop access, the
three tray values and manual Retry/Cancel button interaction remain unchecked.
