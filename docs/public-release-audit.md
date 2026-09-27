# Public repository release audit

Audit date: 2026-09-25; history rescan and final Linux preflight updated 2026-09-27

Scope: the remotely installed sanitized history, its tracked file history,
commit/tag metadata, and the fresh-clone working tree relevant to a future
public release. Repository visibility and production state were not changed.

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

1. The original history used a personal author and committer email. The
   rewritten reachable history uses the owner-approved GitHub noreply address
   while preserving historical names and dates; the old address now has zero
   reachable metadata or content hits.
2. The original history contained a private Linux deployment host name, LAN
   address/subnet, service user, operational paths, and a host-bearing filename.
   Neutral replacements preserve the useful technical history, and the final
   fresh-clone scan found zero original-value hits.
3. The original README/install/deployment history included an old private
   clone/repository reference. Rewritten history and current public-facing docs
   use neutral placeholders instead.
4. The exact historical inventory, classifications, ref scope, rewrite command,
   GitHub residual-exposure review, and verification gates are recorded in
   `docs/history-sanitation-plan.md`.

## Current-tree remediation

- Replaced the machine-specific deployment record with a public-safe boundary.
- Removed the personal Linux development username from tracked policy/status
  examples.
- Removed the exact personal email from current audit prose and rewrote author,
  committer, and tagger email to the owner-approved GitHub noreply address while
  preserving historical names and dates.
- Replaced private clone URLs with launch placeholders.
- Added ignores for temporary screenshots, `node_modules`, Cargo `target`, and
  generated Tauri ACL/schema output.

## Publication blockers

- History sanitation is **REMOTE HISTORY SANITATION COMPLETE**. The exact
  validated refs were installed atomically with explicit leases; the fresh
  clone has zero approved historical-infrastructure or old-email hits,
  preserved topology and dates, and clean integrity and secret scans.
- FlightMargin naming, AGPLv3-or-later application, and the current-tree
  privacy audit are complete.
- The repository must be deliberately made public only after the final audit.
- Public security contact/private vulnerability reporting must be enabled.
- Signing, final artifact, and release approval gates remain open. Version
  `0.3.0-beta.1` is approved but no tag or release is authorized.
- The intended future repository rename to `flightmargin` remains subject to
  availability and explicit publication approval.

## Final Linux preflight

The sanitized active Linux checkout passed strict Git integrity and
reachable-history/current-tree privacy and focused secret scans. The current
tracked tree contains no credentials, populated authentication files,
databases, logs, private screenshots, generated build trees, backup bundles,
or history-rewrite maps. `.gitignore` excludes local virtual environments,
build output, runtime databases, environment files, temporary files, desktop
build output, and test caches.

The package was built and verified as `flightmargin 0.3.0b1` under
`AGPL-3.0-or-later`; canonical and legacy CLI aliases, authenticated Codex
collection, and isolated FlightMargin dashboard/Settings routes passed. The
generated `flightmargin.service` and legacy-compatible `codex-quota.service`
units passed static systemd verification. No system-manager unit was installed
and no production resource was modified.

Public repository preparation is documentation-only: the intended name is
`flightmargin` at `gmstd66/flightmargin`; recommended description is “A
lightweight, local-first monitor for OpenAI Codex usage limits, pacing, resets,
credits, and history.” Recommended topics are `codex`, `openai`, `quota`,
`usage-monitor`, `rate-limits`, `windows`, `linux`, `tauri`, and `python`.
Source, issue, and Sponsor links remain disabled until that destination exists.
