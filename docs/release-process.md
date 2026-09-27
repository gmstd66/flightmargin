# Public beta release process

This is the owner-approved process for preparing FlightMargin Beta 1. Tagging
and publication remain protected human gates.

## Beta 1 flow

```text
reviewed release-candidate commit on dev/productization
  -> fast-forward main to the exact candidate commit
  -> manually dispatch the GitHub-hosted Windows workflow on main
  -> tests and unsigned NSIS artifact
  -> independently verify the installer SHA-256
  -> record Defender, SmartScreen, and native validation results
  -> owner reviews the exact source, artifact, and release notes
  -> owner separately approves tag and GitHub prerelease publication
```

Pushing an ordinary commit must never publish an installer. The current
workflow uses `workflow_dispatch`, uploads a short-lived unsigned Actions
artifact, and has read-only repository contents permission. It does not sign,
tag, or publish anything.

FlightMargin `0.3.0-beta.1` is intentionally unsigned. Authenticode/SignPath
approval, configuration, and secrets are not Beta 1 gates and must not be
simulated. The published installer must be accompanied by its SHA-256 file,
and that checksum must be calculated independently before publication.
Unknown Publisher and Microsoft Defender SmartScreen behavior must be recorded
with Defender left enabled.

## First beta update policy

Users update manually from GitHub Releases and must fully Quit the app before
an upgrade. Tauri auto-update is deferred until the manual build and publish
process is stable. Future updater private keys would be separate protected
release credentials.

## Post-beta signing review

SignPath remains a possible improvement after Beta 1. Reconsider it when
adoption, user feedback, repeated SmartScreen friction, or another concrete
need justifies the operational process. See [code-signing.md](code-signing.md)
for retained research. No signing secrets or configuration are currently
required.

## Sponsorship

Sponsorship remains deferred. Beta 1 has no Sponsor action, `FUNDING.yml`, or
donation button. Any future sponsorship activation requires a separate owner
decision and a real destination.
