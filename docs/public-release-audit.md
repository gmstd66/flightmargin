# Public repository release audit

Audit date: 2026-09-25; history rescan updated 2026-09-27

Scope: the locally sanitized candidate's current tracked files, all 56
reachable commits and 764 reachable object/path entries, tracked file history,
commit/tag metadata, and the working tree relevant to a future public release.
No GitHub ref, repository visibility, or production state was changed.

## Secret scan

- Scanned all candidate-reachable commit trees and messages plus the annotated
  tag for private-key headers and common GitHub, OpenAI-style, AWS, Google,
  bearer-token, JWT, credentialed-connection-string, and related patterns.
- Searched the current tree for credential assignments, authentication-file
  references, personal email patterns, absolute user paths, private network
  addresses, logs, databases, and credential-like filenames.
- Found **no high-confidence secret, token, private key, password, tracked
  database, tracked log, tracked authentication file, or tracked user
  screenshot**.
- `auth.json` appears only in documentation/tests that explicitly warn users
  not to expose it; no contents or checksum are present.

This focused scan is evidence, not a guarantee. A dedicated scanner such as
Gitleaks should be added to the public CI/security process after repository
visibility and policy are approved.

## Privacy and infrastructure findings

1. Every baseline-reachable commit uses the same personal author and committer
   email. Making the repository public will expose it through raw Git history.
   This is not an application secret, but it is a personal privacy decision. A
   checked-in `.mailmap` changes display in some tools but does not remove the
   original metadata.
2. Earlier commits contain a private Linux deployment host name, LAN
   address/subnet, service user, and operational paths. Current tracked
   documentation has been sanitized and the public documentation now retains
   only the production-protection boundary. Historical copies remain reachable.
3. Earlier README/install/deployment documentation includes the old private
   GitHub clone/repository reference. Public-facing current docs use a launch
   placeholder instead.
4. The exact historical inventory, classifications, ref scope, rewrite command,
   GitHub residual-exposure review, and verification gates are recorded in
   `docs/history-sanitation-plan.md`.

## Current-tree remediation

- Replaced the machine-specific deployment record with a public-safe boundary.
- Removed the personal Linux development username from tracked policy/status
  examples.
- Removed the exact personal email from current audit prose. The locally
  validated candidate rewrites author, committer, and tagger email to the
  owner-approved GitHub noreply address while preserving historical names and
  dates.
- Replaced private clone URLs with launch placeholders.
- Added ignores for temporary screenshots, `node_modules`, Cargo `target`, and
  generated Tauri ACL/schema output.

## Publication blockers

- History sanitation is **LOCAL SANITIZED HISTORY VALIDATED — REMOTE UPDATE
  PENDING**. The private candidate has zero approved historical-infrastructure
  or old-email hits, identical pre/post rewrite HEAD trees, preserved topology
  and dates, clean integrity/secret scans, and complete functional validation.
- GitHub still contains the old history. The exact atomic leased force-update
  requires separate explicit approval; no remote ref was rewritten or deleted.
- FlightMargin naming and AGPLv3-or-later application are complete; a final
  current-tree audit must confirm the renamed artifacts and notices.
- The repository must be deliberately made public only after the final audit.
- Public security contact/private vulnerability reporting must be enabled.
- Signing, final artifact, and release approval gates remain open. Version
  `0.3.0-beta.1` is approved but no tag or release is authorized.
- The intended future repository rename to `flightmargin` remains subject to
  availability and explicit publication approval.
