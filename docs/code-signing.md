# Windows code-signing plan (post-Beta 1)

FlightMargin `0.3.0-beta.1` is intentionally unsigned. Code signing is not a
Beta 1 release gate. No SignPath application, signing account, secret, fake
configuration, or signing job is required for Beta 1.

Beta 1 instead requires a GitHub-hosted build, a published SHA-256 file with an
independent checksum match, and recorded Microsoft Defender and
SmartScreen/Unknown Publisher behavior. User documentation must explain the
unsigned status without telling users to weaken or blindly bypass Windows
security controls.

## When to reconsider signing

SignPath Foundation remains a possible post-beta improvement. Reconsider it
when demonstrated adoption, user feedback, recurring SmartScreen friction, or
another concrete distribution need justifies the application, review, and
credential-management process. Do not implement speculative signing
configuration before that decision.

## Retained SignPath research

SignPath Foundation's published
[conditions for open-source projects](https://signpath.org/terms.html) include,
among other things:

- an OSI-approved open-source license for project components, without
  commercial dual licensing;
- a public, maintained, documented, already released project;
- no proprietary project components in the signed package, subject to its
  documented treatment of system libraries and unsigned upstream components;
- a verifiable relationship between source, trusted automated build, and the
  signed binary;
- MFA for repository and SignPath access;
- documented committer, reviewer, and approver roles with manual approval;
- a published code-signing policy and privacy statement.

The public repository and manual GitHub-hosted workflow establish useful
provenance, but they do not imply SignPath eligibility or acceptance.

If signing is later approved, the intended boundary is:

```text
approved source/tag
  -> GitHub-hosted Windows build and tests
  -> unsigned NSIS artifact
  -> verified SignPath origin and signing request
  -> manual signing approval
  -> signed installer returned to automation
  -> checksum calculated from the signed file
  -> human-reviewed GitHub release
```

The application executable and installer should be covered when supported by
the approved artifact configuration. A provider-held signing key should never
be exported into GitHub Actions. Exact organization, project, policy, artifact,
and credential values must come from an accepted project; placeholders must
not be committed. Credentials would require a protected GitHub environment,
minimum permissions, and human reviewers.

If SignPath is unsuitable, paid signing or Microsoft Store distribution would
require a separate owner decision covering cost, identity, key custody,
timestamping, renewal, workflow security, and support impact.
