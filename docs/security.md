# Security and privacy

## Boundaries

The CLI does not contact networks or execute installers. Original sessions,
databases, installers and logs are opened read-only. No source is rewritten,
deleted, decompressed in place, or committed. Generated artifacts are private and
must live outside repositories. `integrate` writes a copy and diff; it never
runs Paxel. MIT applies only to this project's code, not YC's installer.

Diagnostics contain aggregate counts, issue codes, hashed source/session IDs,
path-free explanations and attribution rules. `--show-paths` opts into private path
output. Hashes are linkable pseudonyms and may reveal information to someone who
already knows candidate paths. Review all diagnostics before sharing.
Prepared transcripts contain complete private conversations. Paxel sidecars and
generated runner patches contain recorded paths/remotes or recovery locations.
They are not sanitized bug-report attachments. Do not upload them to public issues.

## Threat model

Treat transcripts, filenames, session IDs, metadata, compressed bytes and SQLite
schemas as untrusted. User-selected roots, installer fingerprints, the Python
runtime and the private output parent are trusted. An attacker controlling this
process, the same user account, writable ancestors, interpreter, or official Paxel
container can defeat these guarantees. This is not an OS sandbox or malware scanner.

Controls:

- No-follow regular-file source opens; storage traversal does not follow symlinks.
- Storage/output symlink ancestors are rejected except verified standard macOS
  `/tmp` and `/var` aliases. Recorded metadata symlinks are resolved only for scope.
- Path-component containment prevents similar-prefix and `..` scope errors.
- Hash-generated names prevent traversal via IDs, remotes or cwd strings.
- No transcript metadata enters shell interpolation or SQL statements.
- 512 MiB expanded-byte default per file, 8 MiB line cap, 128 MiB Zstandard window,
  2 MiB database field cap, bounded wire fields and SQLite progress limit reduce resource abuse.
  There is no global time/disk quota: choose narrow roots for hostile inventories.
- SQLite extension loading is never enabled; queries are fixed, read-only and
  immutable only without WAL or rollback journals. Active data is not silently ignored.
- Malformed, conflicting and boundary-crossing sessions are excluded.
- Directory staging, per-file fsync, exclusive output reservation and atomic rename avoid publishing incomplete
  preparation. Exceptions clean up staging data. Source hashes detect changed
  content between inventory and preparation; source growth is refused before excess bytes are written.
- Output mode `0700` / file mode `0600`, no overwrite of existing output directories,
  and refusal to write private output inside Git reduce accidental disclosure.
  OS crash/power-loss durability of directory rename is not guaranteed.
- Complete runner fingerprints, unique anchors, `bash -n`, reviewable diffs and an
  explicit upload-consent environment variable guard integration. Before original
  startup, the generated runner invokes the installed CLI to check the pinned
  manifest hash, transcript hashes and sidecar hash. Keep that installation available;
  regenerate integration after moving or replacing its Python environment.

No-follow checking is not a defense against malicious same-user concurrent ancestor
replacement. Do not use world-writable output parents for sensitive recovery. Use
a private directory under your home folder. A live IDE may change source data;
close it and retry if hashes or attribution become inconsistent.

## External execution

The official runner may contact authentication, container registries, model proxies,
analysis/upload endpoints and replay previous pending uploads. Its exact current
behavior and data handling are governed by YC, not this project. Review the original
installer and official terms before execution. The generated copy retains these
controls and requires `PAXEL_WORKSPACE_ALLOW_UPLOAD=YES`; this is an explicit consent
signal, not a technical guarantee that data stays local.

Prepared-only mode disables other agent collectors and source repository mounting.
It preserves downstream parsing/scoring/reporting, which cannot be validated solely
by reading the Bash installer. Mutable external images may change. Compare actual
run logs with the manifest and inspect report/upload results independently.

## Reporting issues

Use sanitized JSON diagnostics and the installer SHA-256. Never attach raw
transcripts, SQLite databases, sidecars, private paths, authentication state, or
full Paxel logs. If a credential is exposed, revoke it with its provider before
sharing a minimal report. Open a private report for sensitive findings.

## Release hardening notes

Generated verification runs Python with `-I`, so a package in the current project
or PYTHONPATH cannot replace the verifier. Bash syntax checks use a system-search
executable and a minimal environment, with a timeout and no stdin. The explicit
collector overrides contain no eval. The script itself must still be invoked from
a trusted shell: Bash can read caller-controlled startup environment before its
script gate, and compromised interpreter installations remain outside our boundary.

Metadata reads are bounded independently of prior stat results. Immutable SQLite
reads reject both WAL and rollback journals, require an actual metadata table, and
turn trusted schema off. Preparation refuses a source that grows beyond inventoried
bytes before writing the extra block; a conservative output estimate includes
headers, sidecar and manifest overhead. Other concurrent disk users can still cause
ENOSPC; failed staging is cleaned up. SIGKILL/power loss may leave a private staging
directory; inspect and obtain approval before deleting generated artifacts.

Offline secret scans cover intended source plus reachable Git blobs/commit/tag
objects. This does not automatically certify personal data or unreachable remote
resources. Commit identities and user-supplied attachments need separate manual review.
