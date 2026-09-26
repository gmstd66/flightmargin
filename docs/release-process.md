# Public beta release process

This is a design for a future owner-approved release. It is not active public
automation.

## Human-gated flow

```text
owner approves product name, license, version, and release
  -> version bump on an approved branch
  -> reviewed merge to main
  -> signed version tag
  -> manually approved GitHub Actions candidate build
  -> tests and unsigned NSIS artifact
  -> SignPath origin verification and manual signing approval
  -> signed installer and final checksum verification
  -> owner reviews release notes and clean-machine results
  -> GitHub prerelease is published manually
```

Pushing an ordinary commit must never publish an installer. The current
workflow uses `workflow_dispatch`, uploads a short-lived unsigned Actions
artifact, and has read-only repository contents permission. It does not create
a tag or release and does not sign anything.

## First beta update policy

`0.3.0-beta.1` is the recommended first version, pending approval. Users update
manually from GitHub Releases and must fully Quit the app before upgrade. Tauri
auto-update is deferred until the manual build/sign/publish process is stable.
Future updater private keys are separate sensitive release credentials and must
use protected storage, rotation, backup, and reviewer policies.

## Sponsorship launch TODO

The software remains free, with no paid feature tier. Voluntary support is the
only approved sustainability model.

After a real destination exists:

- configure GitHub Sponsors;
- add `.github/FUNDING.yml` with the real sponsor identity;
- enable the repository Sponsor button;
- add the real Sponsor URL to About;
- verify Source Code and Report an Issue URLs at the same time.

Launch configuration must replace the README's `<owner>/<repository>` clone
placeholder and add three reviewed About actions: the public repository root,
the repository's issue-reporting page, and the real GitHub Sponsors profile.
They are intentionally absent from the current app rather than disabled links.

Do not add placeholder URLs or enable these actions before public launch.
