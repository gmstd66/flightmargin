# Windows code-signing plan

Target: SignPath Foundation open-source code signing, if the project qualifies.
No application, account, credential, or signing job is created by milestone
6.20D.1; signing remains the following protected phase.

## Eligibility dependencies

SignPath Foundation's published
[conditions for open-source projects](https://signpath.org/terms.html) require,
among other things:

- an OSI-approved open-source license for all project components, without
  commercial dual licensing;
- a public, maintained, documented, already released project;
- no proprietary project components in the signed package (system libraries
  and unsigned upstream OSS components are addressed separately by its terms);
- a verifiable relationship between source, trusted automated build, and signed
  binary;
- MFA for repository and SignPath access;
- documented committer/reviewer/approver roles and manual signing approval;
- a published code-signing policy and privacy statement.

The repository is private and has no public release or SignPath acceptance.
The AGPLv3-or-later license is now applied through `LICENSE`; public project
history and the other eligibility conditions remain prerequisites, not CI
details that should be mocked.

## Intended integration

The manual Windows candidate workflow in
`.github/workflows/windows-beta-build.yml` establishes the unsigned trusted
build boundary: GitHub-hosted Windows runner, locked Node/Rust dependencies,
resolved Python build requirements, tests, NSIS build, and checksum.

After SignPath acceptance, the release workflow should:

```text
approved source/tag
  -> GitHub-hosted Windows build and tests
  -> unsigned NSIS artifact
  -> SignPath origin verification and signing request
  -> manual signing approval
  -> signed installer returned to GitHub Actions
  -> signed-file SHA-256 checksum
  -> human-reviewed GitHub prerelease
```

Signing should occur after the build and before the final checksum/release
upload. The Windows application executable and installer should be covered as
supported by the approved SignPath artifact configuration. SignPath's HSM-held
certificate/key should never be exported into GitHub Actions.

## Future protected configuration

The exact values and secret names must come from the accepted SignPath project,
not placeholders. The integration is expected to require identifiers for the
SignPath organization/project, signing policy, artifact configuration, and an
authentication token or approved GitHub integration. Store credentials in a
protected GitHub release environment with required human reviewers and minimum
workflow permissions.

Before enabling signing, publish a **FlightMargin code signing policy** containing the text
and roles required by SignPath, link the privacy policy, protect release
branches/tags, require review of workflow/build changes, and verify artifact
metadata consistently uses the approved product name and version.

## Public distribution

Only the signed installer and its checksum should enter the final GitHub
prerelease. Preserve the unsigned CI artifact for provenance/debugging according
to a documented retention policy, but do not present it as the preferred public
download once signing is active.

If SignPath does not accept the project, paid signing requires a separate owner
decision covering provider, cost, organization identity, key custody,
timestamping, renewal, and CI integration. Microsoft Store distribution remains
a future alternative rather than the primary channel.
