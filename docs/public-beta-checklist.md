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
- [ ] Exact release-candidate source is identical on `main` and `dev/productization`
- [ ] Source corresponding exactly to the candidate binary is public
- [ ] Tag `v0.3.0-beta.1` approved and created (publication gate; not part of 6.21A)

## Candidate build

- [ ] GitHub-hosted Windows workflow succeeds for the exact RC commit on `main`
- [x] Python, npm, and Cargo resolved dependency inputs reviewed
- [x] PyInstaller sidecar rebuilt from current dashboard assets locally
- [x] Local Tauri release and NSIS installer build succeeds
- [x] Unsigned installer status and expected Windows warnings documented
- [ ] Installer SHA-256 produced and independently checked
- [x] Checksum-verification instructions reviewed

## Native validation

- [ ] Windows 11 x64 installation passes using the CI-built installer
- [ ] Existing Codex CLI is detected; Codex is not bundled
- [ ] Authenticated health/quota reads pass
- [ ] Dashboard and Weekly History render correctly without visible consoles
- [ ] Weekly, 5-hour, and Credits tray indicators pass
- [ ] Settings, About, Source Code, Report an Issue, and sanitized Copy diagnostics pass
- [ ] Close-to-tray, single-instance, relaunch, and Quit cleanup pass
- [ ] Transition from the internal 0.2.0 build copies legacy data without loss
- [ ] Running-app installer Retry/Cancel behavior passes
- [ ] Uninstall succeeds and documented user-data preservation is accurate
- [ ] SmartScreen/Unknown Publisher behavior recorded without evasion
- [ ] Microsoft Defender result recorded without disabling protection

## Public presentation and release

- [x] README contains no screenshot or private data
- [x] Installation/privacy/troubleshooting docs reviewed for the candidate
- [x] Third-party notice inventory reviewed against exact release lockfiles
- [ ] Source Code URL enabled and validated in desktop and browser About
- [ ] Report an Issue URL enabled and validated in desktop and browser About
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
