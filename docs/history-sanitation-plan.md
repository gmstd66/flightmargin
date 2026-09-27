# Pre-public Git history sanitation plan

Status: **REMOTE HISTORY SANITATION COMPLETE**

Prepared: 2026-09-27

Baseline: `c5ff3241cb113b38ca37ea4734919ee7bbaca387` on
`dev/productization`. This document records the one owner-authorized rewrite;
it authorizes no further rewrite, force-push, ref deletion, repository rename,
visibility change, release, or production change.

Local execution was completed on 2026-09-27 from authoritative source commit
`b2120b12c0309e598d43a184f80f147e15b10885` in a fresh private mirror. All
approved infrastructure values and the historical personal email were removed
from reachable candidate history. The pre-rewrite and rewritten development
heads had the identical tree `d1c27b559ee439352c90618cf0c1e9eb76b78625`.
On 2026-09-27, the exact validated `main`, `dev/productization`, and annotated
`v0.1-baseline` refs were installed on GitHub in one atomic transaction with
explicit old-OID leases. Independent remote verification and a fresh clone
confirmed the sanitized refs. The repository remained private throughout.

The candidate retained 55 mapped commits, one merge, one root, two branches,
and one annotated tag before this validation-status commit. All mapped parent
relationships, author/committer names and dates, and messages matched, except
for the approved private-host placeholder. The tag target mapping, tagger name
and date, and annotation semantics also matched. Strict `git fsck`, the
historical privacy scan, and the focused secret scan passed.

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
sanitized-candidate bundle named
`flightmargin-sanitized-candidate-20260927-final.bundle` was also verified
before the remote update. Its SHA-256 is
`70F5FE86AEF5A0812047D15488941CCC74C47DD7514575978D08A43940A90272`.
Both bundles remain outside Git in the private owner backup directory.

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
| Personal author email | 54 of 54 in author and committer metadata; 7 also in file content | `docs/public-release-audit.md` for content | metadata and content; the annotated tag also has the address in tagger metadata | `67e586f` / `c5ff324` | absent from the rewritten reachable history | **REPLACED** with the owner-approved noreply address while preserving names and dates |
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

The owner selected option 2 for local execution:

1. **Preserve metadata** was rejected.
2. **Replace the email in the same rewrite** was executed with the exact
   owner-approved GitHub noreply address. Both historical name spellings were
   retained without normalization, together with author/committer/tagger dates,
   messages, and ordering.

The selected address is owner-approved for GitHub attribution. The literal
address is intentionally not repeated in this public-facing plan.

## Executed rewrite design

The rewrite used `git-filter-repo` 2.47.0, not `git filter-branch`, from an
isolated private maintenance environment. It was suitable because it has
first-class content, commit/tag message, path-renaming, and mailmap filters and
produces commit/ref maps for review.

The dry run and actual rewrite ran in separate fresh private mirror clones, not
in the normal working checkout. Exact source paths, replacement files, and the
mailmap remained outside Git and outside the repository. The reviewed
replacement file applied longer strings before contained identities and used
this semantic map:

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

The reviewed command shape was:

```powershell
git filter-repo --dry-run `
  --path-rename '<private-host-bearing-source-path>:docs/private-deployment-record.md' `
  --replace-text <private-content-replacements-file> `
  --replace-message <private-message-replacements-file> `
  --preserve-commit-hashes --preserve-commit-encoding `
  --prune-empty never --prune-degenerate never `
  --replace-refs delete-no-add
```

The dry-run exports were reviewed before running the identical command without
`--dry-run` in the execution mirror. The owner chose email replacement, so the
execution included:

```text
--mailmap <private-owner-approved-mailmap>
```

Do not use `--force` to bypass the fresh-clone safety check. Default all-ref
filtering preserves branch/merge topology while rewriting affected commits,
trees, blobs, and the annotated tag. `--prune-* never` prevents commit or merge
removal. Author and committer dates are retained. Commit and tag messages are
retained byte-for-byte except for the approved private-host substitution; the
hash and encoding preservation flags prevent unrelated message rewrites.

## Affected refs and executed publication transaction

The private infrastructure first appears after the baseline tag's target
commit, but the tag annotation itself contains the private host identifier.
Accordingly, the authorized transaction changed:

| Ref | Result |
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

The executed push had explicit owner approval and all three exact old-OID
leases matched. A lease mismatch would have aborted the transaction; blind
`--force` was not used. No unreviewed, replacement, backup, or
`refs/original/*` refs were pushed, and no remote branch cleanup was needed.

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

The current FlightMargin tree and all rewritten reachable history are clear of
the inventoried private host, LAN, service-user/personal Linux identity,
private development path, old clone/repository reference, and historical
host-bearing filename. The exact personal email is absent from reachable file
content and Git metadata; the approved noreply address is used instead while
historical identity names and dates remain unchanged. Generic
documentation/test addresses, test users, compatibility identifiers, and the
protected generic production boundary are intentionally retained.

## Post-rewrite verification record

The following checks were completed against the isolated candidate before the
push and repeated where applicable from the fresh post-push clone:

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

Local validation and the owner-authorized atomic leased GitHub update are
complete. Post-push verification confirmed the two expected branches, the
sanitized annotated baseline tag, a clean fresh-clone integrity check, zero
approved privacy-value hits, and no high-confidence secrets. The original
checkout and both bundles still contain or may contain private historical
material and must remain private. Any Linux development checkout made before
the rewrite must be replaced with a fresh clone before further development.

Repository rename, public visibility, merge to `main`, tag/release publication,
and production changes remain separate protected gates.
