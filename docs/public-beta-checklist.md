# Windows public beta release checklist

All gates are intentionally unchecked. Completion requires current evidence for
the exact release commit and artifact.

## Product and legal

- [x] FlightMargin public product name approved; ReserveLight retained as fallback
- [x] Selected AGPLv3-or-later terms applied through a reviewed `LICENSE`
- [x] Contribution terms set to the project `AGPL-3.0-or-later` license
- [x] History sanitation documented: **PLANNED — NOT YET EXECUTED**
- [ ] Historical author-email/private-infrastructure exposure accepted or remediated
- [ ] Repository audit rerun and clean
- [ ] Public security reporting channel enabled
- [ ] Repository intentionally made public

## Version and source

- [x] Public version approved as `0.3.0-beta.1`
- [x] Canonical version updated once and synchronized across generated manifests
- [ ] Release branch/main state reviewed and approved
- [ ] Signed tag `v0.3.0-beta.1` approved and created
- [ ] Source corresponding exactly to the binary is publicly available

## Build and signing

- [ ] GitHub-hosted Windows workflow passes from the approved tag
- [ ] Python, npm, and Cargo resolved dependency inputs reviewed
- [ ] PyInstaller sidecar rebuilt from current dashboard assets
- [ ] Tauri release and NSIS installer pass
- [ ] SignPath eligibility/application approved or alternative signing approved
- [ ] Signing origin and artifact configuration verified
- [ ] Executable/installer signature and timestamp verified
- [ ] Final signed-installer SHA-256 produced and independently checked

## Native validation

- [ ] Clean Windows 11 x64 installation passes
- [ ] Existing Codex CLI is detected; Codex is not bundled
- [ ] Authenticated health/quota reads pass
- [ ] Dashboard and Weekly History render correctly without visible consoles
- [ ] Weekly, 5-hour, and Credits tray indicators pass
- [ ] Settings, About, and sanitized Copy diagnostics pass
- [ ] Close-to-tray, single-instance, relaunch, and Quit cleanup pass
- [ ] Upgrade from the previous public beta preserves data/preferences
- [ ] Transition from the internal 0.2.0 build copies legacy data without loss
- [ ] Running-app installer prompt/Retry behavior passes
- [ ] Uninstall succeeds and documented user-data preservation is accurate
- [ ] SmartScreen behavior recorded
- [ ] Defender result recorded without disabling protection

## Public presentation and release

- [ ] README screenshot reviewed for private data
- [ ] Installation/privacy/troubleshooting docs final
- [ ] Third-party notices generated and reviewed
- [ ] Source Code URL enabled in About
- [ ] Report an Issue URL enabled in About
- [ ] GitHub Sponsors configured and Sponsor URL/FUNDING.yml enabled, or explicitly deferred
- [ ] Release notes reviewed
- [ ] GitHub prerelease created only after final human approval
- [ ] Installer and checksum attached to the prerelease

Auto-update is deliberately excluded from beta 1 and remains a later decision.
