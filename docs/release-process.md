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

## Published Beta 1 evidence

FlightMargin `0.3.0-beta.1` was published as a GitHub prerelease after separate
owner authorization. Annotated tag `v0.3.0-beta.1` points to validated binary
source commit `c9a25dd78e9ab01c5b2ea83abe0c4e923e09111b`; later commits only record
acceptance and release evidence. GitHub Actions run `36356858138` produced the
published `FlightMargin-0.3.0-beta.1-Windows-x64.exe`, whose SHA-256 is
`d742da49292c5166c49f0e5bd0621fae963dbebbd06f4d1a2262b079441bfeec`.

The public installer and checksum were downloaded anonymously after publication
and verified again. The checksum matched exactly, the release retained
prerelease status, and the installer retained its intentional `NotSigned`
status. Publication did not add signing, Sponsor, package distribution,
auto-update, or production changes.
