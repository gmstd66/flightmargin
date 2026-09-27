# Pre-public Git history sanitation plan

Status: **PLANNED — NOT YET EXECUTED**

Prepared: 2026-09-27

Baseline: `c5ff3241cb113b38ca37ea4734919ee7bbaca387` on
`dev/productization`. This document authorizes no rewrite, force-push, ref
deletion, repository rename, visibility change, release, or production change.

## Repository state and backup

The working tree was clean before this milestone, so no uncommitted owner work
was at risk. The live GitHub remote was checked after a non-pruning fetch.

| Item | Recorded state |
| --- | --- |
| Current branch and baseline HEAD | `dev/productization` at `c5ff3241cb113b38ca37ea4734919ee7bbaca387` |
| `origin/dev/productization` | `c5ff3241cb113b38ca37ea4734919ee7bbaca387` |
| Default branch | `main` |
| Local branches | `dev/productization` at `c5ff324`; `main` at `72a5594` |
| Remote branches | `origin/dev/productization` at `c5ff324`; `origin/main` and symbolic `origin/HEAD` at `72a5594` |
| Tags | annotated `v0.1-baseline`, tag object `ad70aad`, peeled commit `67e586f` |
| Working tree | clean and synchronized with `origin/dev/productization` |

The authoritative pre-rewrite bundle is named
`flightmargin-pre-public-history-backup-20260927-c5ff324.bundle`. It is outside
the working tree in the private owner backup directory, is 292,518 bytes, and
has SHA-256
`A76A6C8819D99C4488EA4A3660BA84951FF955663C7DAC826D403C1537896DD9`.
`git bundle verify` reported that it is valid and records complete history with
all seven then-reachable local, remote-tracking, tag, and HEAD refs. The bundle
must remain private and must not be uploaded or added to Git. A second fresh
bundle must be taken immediately before the future authorized rewrite because
this planning commit postdates the recorded bundle.

## Inventory method

The rescan covered all 54 commits and 747 reachable object/path entries at the
baseline. Counts below mean reachable commits whose complete tree contains a
value; commit/tag messages and identity metadata were checked separately. The
planning commit adds one commit but deliberately adds none of the literal
private infrastructure values.

Sensitive values are not repeated here. The private execution inputs must be
built from the locally reviewed values and stored outside the repository.

| Category | Affected commits at baseline | Affected paths | Location | Oldest / newest affected commit | Current-tree state | Classification and need |
| --- | ---: | --- | --- | --- | --- | --- |
| Personal author email | 54 of 54 in author and committer metadata; 7 also in file content | `docs/public-release-audit.md` for content | metadata and content; the annotated tag also has the address in tagger metadata | `67e586f` / `c5ff324` | exact address removed from current documentation in this milestone; metadata remains | **OWNER DECISION** for metadata; replace historical documentation text regardless |
| Private Linux host identifier | 46 | `README.md`, `docs/architecture.md`, `docs/deployment-<private-host>.md`, `docs/project-status.md` | content; one commit message and the annotated tag message also contain it | `7244c16` / `59ccbba` | absent | **REPLACE** with `<private-host>`; rename the historical host-bearing path |
| Private LAN address/subnet | 46 | `docs/deployment-<private-host>.md` | content | `7244c16` / `59ccbba` | absent; generic example/test addresses remain | **REPLACE** with neutral LAN placeholders |
| Service-user/personal Linux identity | 48 | `AGENTS.md`, `docs/deployment-<private-host>.md`, `docs/platform-parity.md`, `docs/project-status.md` | content | `7244c16` / `c5ff324` | final current-tree occurrence replaced in this milestone | **REPLACE** with `<service-user>` where not already covered by a path replacement |
| Private development/operational path | 33 | `AGENTS.md`, `docs/platform-parity.md`, `docs/project-status.md` | content | `a0ce479` / `c5ff324` | final current-tree occurrence replaced in this milestone | **REPLACE** with `<private-development-path>` |
| Old private GitHub clone/repository reference | 46 | `README.md`, `docs/deployment-<private-host>.md`, `docs/installation-linux.md` | content | `7244c16` / `59ccbba` | absent | **REPLACE** with `<owner>/<repository>` forms |

The service identity and private development path overlap, so their counts
must not be added. The host-bearing historical filename is itself part of the
host exposure and needs a neutral historical filename.

### Keep legitimate history

The following are intentionally **KEEP**, not sanitation targets:

- the old product name, internal versions, compatibility notes, architecture
  decisions, and release chronology;
- `codex-quota`, `CODEX_QUOTA_*`, and related documented compatibility
  identifiers;
- generic localhost, example private-network, test-user, and test-path values;
- generic production-protection concepts, including the protected production
  layout recorded by policy;
- public GitHub ownership where it is part of a legitimate identifier rather
  than the old private clone/repository reference.

The generic protected production layout occurs throughout all baseline commit
trees. Removing it would damage useful operational history and would not remove
a machine-unique identifier, so it is not a rewrite target.

## Secret scan

The focused scan found **no high-confidence secret** and therefore no rotation
blocker. It checked all reachable commit trees and messages plus the annotated
tag for:

- OpenAI/API, GitHub, AWS, Google, Slack, and Stripe token patterns;
- private-key headers, JWTs, bearer tokens, credential-bearing connection
  strings, and credential assignment patterns;
- populated authentication JSON fields and paths named like authentication,
  credential, environment, key, or certificate files;
- tracked database, SQLite, and log filenames.

No token, private key, password, populated authentication file, credentialed
connection string, tracked database, or tracked log was found. `auth.json`
continues to appear only as a warning/documentation concept, not as tracked
content. No dedicated scanner is installed locally; the explicit pattern scan
is strong evidence, not a mathematical guarantee. The same checks plus a
dedicated scanner such as Gitleaks should run on the isolated candidate before
any rewritten ref is pushed.

If a future scan finds a high-confidence secret, the normal rewrite procedure
must stop. The owner must first receive the category and affected object/path,
and credential revocation or rotation must be assessed without printing the
secret.

## Author and committer metadata

The baseline has two author-name spellings and the same two committer-name
spellings. All 54 commits use the same personal email for both author and
committer metadata: 53 use the primary personal name and one uses the account
handle. No bot or GitHub-generated commit identity exists. The annotated
baseline tag uses the primary identity as tagger. After this plan commit, the
same configured identity is expected on 55 of 55 commits; the execution-time
inventory must confirm that count.

Two options remain:

1. **Preserve metadata.** Do not pass `--mailmap`; the personal email remains
   public in raw commit and tag metadata.
2. **Replace the email in the same rewrite.** After the owner supplies an exact
   GitHub noreply or public development address, create a private mailmap with
   one entry for each existing name spelling. Map only the email and retain the
   original names, author/committer dates, messages, and ordering. Apply it in
   the same `git filter-repo` invocation so history is rewritten only once.

Option 2 can preserve GitHub contribution attribution if the selected address
is associated with the owner's GitHub account. An unassociated address can
make contributions fail to link to the profile. No replacement address is
invented or assumed here. The owner must decide before execution.

## Proposed rewrite

Use `git filter-repo`, not `git filter-branch`. It is suitable because it has
first-class content, commit/tag message, path-renaming, and mailmap filters and
produces commit/ref maps for review. It is not currently installed; install and
record a specific version in an isolated maintenance environment before the
authorized run.

Run the dry run and actual rewrite in two separate fresh private mirror clones.
Never run it in the working checkout. Store the exact source path, replacement
files, and optional mailmap outside Git and outside the repository. The
reviewed replacement file must apply longer strings before contained
identities and implement this exact semantic map:

| Input category | Output |
| --- | --- |
| historical deployment-document path/reference | `docs/private-deployment-record.md` |
| private development path | `<private-development-path>` |
| private LAN address | `<private-lan-address>` |
| private LAN subnet | `<private-lan-subnet>` |
| private host identifier | `<private-host>` |
| service-user identity | `<service-user>` |
| old full clone URL | `https://github.com/<owner>/<repository>.git` |
| old owner/repository shorthand | `<owner>/<repository>` |
| personal email when present in file content | `<historical-personal-email>` |

The private message-replacement file contains only the host substitution. It
sanitizes the one commit message and annotated tag message while leaving all
other messages unchanged. The path rename is separate so the historical
filename is neutral. No file is deleted.

From a fresh private mirror, the proposed commands are:

```powershell
git filter-repo --dry-run `
  --path-rename '<private-host-bearing-source-path>:docs/private-deployment-record.md' `
  --replace-text <private-content-replacements-file> `
  --replace-message <private-message-replacements-file> `
  --preserve-commit-hashes --preserve-commit-encoding `
  --prune-empty never --prune-degenerate never `
  --replace-refs delete-no-add
```

Review the dry-run exports, then discard that mirror. In a second fresh mirror,
run the identical command without `--dry-run`. If the owner chooses email
replacement, add exactly:

```text
--mailmap <private-owner-approved-mailmap>
```

Do not use `--force` to bypass the fresh-clone safety check. Default all-ref
filtering preserves branch/merge topology while rewriting affected commits,
trees, blobs, and the annotated tag. `--prune-* never` prevents commit or merge
removal. Author and committer dates are retained. Commit and tag messages are
retained byte-for-byte except for the approved private-host substitution; the
hash and encoding preservation flags prevent unrelated message rewrites.

## Affected refs and publication transaction

The private infrastructure first appears after the baseline tag's target
commit, but the tag annotation itself contains the private host identifier.
Accordingly, the candidate is expected to change:

| Ref | Expected result |
| --- | --- |
| `refs/heads/main` | changes |
| `refs/heads/dev/productization` | changes, including this plan commit |
| Other branches | none exist |
| `refs/tags/v0.1-baseline` | annotated tag object changes; target commit changes only if email metadata is rewritten |

No branch or tag deletion/recreation is required. Immediately before push,
query live remote OIDs again and compare them with the pre-rewrite record. Push
the complete reviewed set atomically with explicit leases:

```powershell
git push --atomic origin `
  --force-with-lease=refs/heads/main:<recorded-old-main-oid> `
  --force-with-lease=refs/heads/dev/productization:<recorded-old-dev-oid> `
  --force-with-lease=refs/tags/v0.1-baseline:<recorded-old-tag-object-oid> `
  refs/heads/main:refs/heads/main `
  refs/heads/dev/productization:refs/heads/dev/productization `
  refs/tags/v0.1-baseline:refs/tags/v0.1-baseline
```

This future push requires explicit owner approval. A lease mismatch aborts the
transaction; never substitute blind `--force`. Do not push unreviewed refs,
replace refs, backup refs, or `refs/original/*`. No remote branch cleanup is
currently indicated.

## GitHub residual exposure

A live `ls-remote` check advertised only `main`, `dev/productization`, and the
baseline tag. No `refs/pull/*/head` refs were advertised. The local environment
has no authenticated GitHub API client, so GitHub Releases and Actions artifact
inventories could not be proved empty from here. Project policy and history say
none was authorized, but the owner must confirm in the private repository UI or
API immediately before execution.

Changing repository refs does not erase old objects from existing clones,
forks, GitHub caches, pull-request refs, workflow artifacts, release assets, or
provider backups. Before public visibility:

- recheck open and closed pull requests and all hidden pull-request refs;
- inspect Releases and release assets, including drafts;
- inspect Actions run artifacts and caches for archived source;
- inspect forks/collaborators and require existing clones to be discarded and
  freshly cloned after the coordinated rewrite;
- ask GitHub Support about cached or pull-request objects if any old object is
  still retrievable after refs and artifacts are cleaned.

The repository is still private and no public pull-request refs were found, so
performing this work before publication is favorable. It is not proof that
every external copy has vanished.

## Current-tree audit

The current FlightMargin tree is now clear of the inventoried private host,
LAN, service-user/personal Linux identity, private development path, and old
clone/repository reference. The exact personal email was also removed from
current documentation, but it remains in Git metadata pending the owner
decision. Generic documentation/test addresses, test users, compatibility
identifiers, and the protected generic production boundary are intentionally
retained.

## Post-rewrite verification

Before any push, perform all checks against the isolated candidate:

1. Verify the just-in-time bundle and record its absolute path, byte size, and
   SHA-256. Save live pre-rewrite heads/tags and the original HEAD tree OID.
2. Inspect `filter-repo/commit-map`, `ref-map`, `changed-refs`, and
   `first-changed-commits`; require the same commit count, one merge, parent
   relationships, author/committer dates, ordering, subjects except the one
   approved substitution, and exactly the expected changed refs.
3. Run `git fsck --full --strict` and confirm that no backup/original/replace
   refs exist in the candidate.
4. Repeat the all-reachable-object secret scan, preferably also with Gitleaks.
5. Search every reachable tree, commit/tag message, filename, author,
   committer, and tagger field for every private input. Require zero historical
   infrastructure hits. For author email, require either zero hits under option
   2 or the explicitly accepted original metadata under option 1.
6. Compare the pre-rewrite and candidate `HEAD^{tree}` OIDs. They must be
   identical. Also compare `git diff --no-index` exports of both HEAD trees and
   require no functional difference.
7. Run the complete Python test suite, `git diff --check`, the established
   release/version checks, and wheel build/verification. Confirm canonical
   `0.3.0-beta.1` and all generated package/Tauri/Cargo mirrors remain aligned.
8. Re-run the current-tree privacy audit independently of the historical scan.
9. Have a second reviewer inspect the candidate and reports before the owner
   authorizes the atomic leased push.
10. After push, query all GitHub heads, tags, and pull-request refs; compare
    remote OIDs to the reviewed candidate, rerun remote-clone scans, and inspect
    Releases, artifacts, caches, and forks/clones as described above.

The sanitized HEAD working tree must be functionally and tree-object identical
to the pre-rewrite HEAD. Only historical objects and, if approved, identity
metadata change.

## Execution gates

Before execution, the owner must decide only:

1. preserve the historical personal email, or provide the exact approved
   GitHub noreply/public development address for the same-pass rewrite; and
2. separately authorize the destructive history rewrite and the atomic
   force-with-lease update after reviewing a fully validated candidate.

Repository rename, public visibility, merge to `main`, tag/release publication,
and production changes remain separate protected gates.
