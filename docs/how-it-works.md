# Why sessions go missing

## Compressed Codex transcripts

The inspected installer recursively discovers `*.jsonl` with a depth limit, while
Codex can archive sessions as `*.jsonl.zst`. Recovery walks both formats and streams
Zstandard expansion into new copies. Inventory parses all lines to detect malformed
files and cwd changes; memory remains bounded by one line plus metadata.

## Repository remotes versus workspace paths

Paxel already has a Codex workspace parameter and cwd bucket helper in the inspected
snapshot. The missing piece is choosing that scope consistently. Its parent-directory
branch invokes a child-repository menu, while sessions launched at the parent often
have no recorded remote. Decompression alone cannot fix that control flow.

The local working patch changed three places: it selected the current directory
instead of the child-repository menu, relaxed the Antigravity no-remote guard when
a workspace scope existed, and filtered temporary Antigravity outputs by synthetic
metadata cwd. It did not modify original transcripts. Its shell path matching and
implicit handling of other agent collectors are not copied into this project.

This tool explicitly selects eligible sessions before integration. It bypasses the
original selection branch only in its generated prepared-only mode and supplies
already grouped buckets at the normal transcript mount. Other collectors are inert,
so their original scope rules cannot accidentally pull in unrelated projects.

## Worktrees, nested repositories and history

A `.git` file marks a worktree-like checkout; a `.git` directory marks a repository.
These annotate path evidence. A historical missing cwd still matches a normalized
descendant path. Worktrees outside the requested workspace remain outside, even
when the same repository remote is present. Symlinks in recorded cwd resolve to
their actual target, so aliases do not create false prefix matches.

Recorded parent-workspace sessions remain workspace-level activity. The tool does
not claim that every current child repository was used. Multiple repositories can
be represented, but any known path outside the boundary causes exclusion rather
than partial-transcript leakage. No elapsed agent activity is reported as human
coding time.

## Antigravity database metadata

The inspected installer extracts printable runs from SQLite's
`trajectory_metadata_blob.data`. These are binary blobs, not ordinary UTF-8 JSON.
The adapter recognizes the locally observed protobuf wire layout: top-level field 1
contains repeated workspace descriptors whose field 1 is the workspace URI; top-level
field 7 mirrors workspace URIs. Descriptor field 2 is an enclosing repository URI,
and other nested file URIs can be generated artifacts. Counting every URI as a
workspace would create false ambiguity. Fixed bounded wire parsing extracts only
these observed workspace slots; captured remotes come from printable evidence.
An unrecognized framing falls back to printable URI candidates with an explicit
UNSTRUCTURED_DATABASE_METADATA warning; independent structured transcript evidence
is required before those sessions become eligible. This is an observed format adapter, not a
complete official schema or a guarantee for future Antigravity versions. URI paths
are decoded and normalized; no arbitrary SQL, extensions, or shell commands run.
Multiple actual workspace descriptors remain explicit evidence.

To avoid writing SQLite companion files, databases with no WAL use read-only
immutable connections and before/after stat checks. An existing WAL triggers a
warning and transcript fallback; immutable mode must never ignore it silently.
Missing tables, unreadable databases and invalid metadata also fall back to
structured `Cwd` fields or a known GENERIC workspace-access notice.

## Pipeline stages

For example, a fictional run might report 100 extracted/parsed sessions,
70 analyzable, 30 too short, 70 summaries and 100 scored work streams. Those are
different stages, not contradictory totals. These illustrative counts are not
hard-coded expectations or observations from a user's private history.

Preparation alone proves neither parsing nor upload. Verify extraction/parsing
counts against one complete approved run log, and inspect official report evidence
separately. See [compatibility limits](compatibility.md).
