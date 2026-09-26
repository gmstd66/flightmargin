# Public repository release audit

Audit date: 2026-09-25

Scope: current tracked files, all 47 reachable commits, tracked file history,
Git metadata, and the local working tree relevant to a future public release.
No repository visibility or history was changed.

## Secret scan

- Scanned 554 reachable Git objects for private-key headers and common GitHub,
  OpenAI-style, AWS, Google, and bearer-token patterns.
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

1. Every reachable commit currently uses the personal author email
   `<historical-personal-email>`. Making the repository public will expose it through
   Git history. This is not an application secret, but it is a personal privacy
   decision. A `.mailmap` changes display in some tools but does not remove the
   original metadata.
2. Earlier commits contain a private Linux deployment host name, LAN
   address/subnet, service user, and operational paths. Current tracked
   documentation has been sanitized and the public documentation now retains
   only the production-protection boundary. Historical copies remain reachable.
3. The repository remote and earlier README/install documentation include the
   current private GitHub owner/repository path. Public-facing current docs use
   a launch placeholder instead.
4. Local untracked owner-review screenshots and generated desktop build trees
   exist in the development checkout. They were not staged, and matching
   temporary/build paths are now ignored. They must not be added to a public
   commit without a separate privacy review.

## Current-tree remediation

- Replaced the machine-specific deployment record with a public-safe boundary.
- Removed the personal Linux development username from tracked policy/status
  examples.
- Replaced private clone URLs with launch placeholders.
- Added ignores for temporary screenshots, `node_modules`, Cargo `target`, and
  generated Tauri ACL/schema output.

## Publication blockers

- Owner must decide whether to accept the historical author-email and private
  infrastructure exposure or authorize a separately planned history rewrite.
  This milestone does not rewrite or force-push history.
- Product name must pass the branding gate in `branding-review.md`.
- The selected AGPLv3-or-later terms must be applied through a reviewed `LICENSE`.
- The repository must be deliberately made public only after the final audit.
- Public security contact/private vulnerability reporting must be enabled.
- Signing, version, final artifact, and release approval gates remain open.
