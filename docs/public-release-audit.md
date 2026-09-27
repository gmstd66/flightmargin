# Public repository release audit

Audit date: 2026-09-25; history rescan, final Linux preflight, and repository
publication updated 2026-09-27

Scope: the remotely installed sanitized history, its tracked file history,
commit/tag metadata, and the fresh-clone working tree. Repository publication
was completed on 2026-09-27; production state was not changed.

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

## Publication status and remaining release blockers

- History sanitation is **REMOTE HISTORY SANITATION COMPLETE**. The exact
  validated refs were installed atomically with explicit leases; the fresh
  clone has zero approved historical-infrastructure or old-email hits,
  preserved topology and dates, and clean integrity and secret scans.
- FlightMargin naming, AGPLv3-or-later application, and the current-tree
  privacy audit are complete.
- `gmstd66/codex-quota-monitor` was renamed to the public repository
  `gmstd66/flightmargin` after the final audit. Its approved description and
  topics were applied, and private vulnerability reporting is enabled.
- Signing, final artifact, and release approval gates remain open. Version
  `0.3.0-beta.1` is approved but no tag or release is authorized.

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

The public repository is `https://github.com/gmstd66/flightmargin`; its issue
destination is `https://github.com/gmstd66/flightmargin/issues`. Its description
is “A lightweight, local-first monitor for OpenAI Codex usage limits, pacing,
resets, credits, and history.” Its topics are `codex`, `openai`, `quota`,
`usage-monitor`, `rate-limits`, `windows`, `linux`, `tauri`, and `python`.
Desktop Source/Issue actions and Sponsor links remain disabled pending separate
approval.
