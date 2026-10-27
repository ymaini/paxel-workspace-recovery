# Compatibility and validation limits

## Agents and storage

Codex `.jsonl` / `.jsonl.zst` and the three documented Antigravity surfaces are
supported for read-only discovery. No other agent adapters are claimed. See the
[Codex](../references/codex-storage.md) and
[Antigravity](../references/antigravity-storage.md) storage references.

Python 3.11–3.13 is the tested version range. macOS and Linux are test targets;
Windows is unsupported. Later Python versions and Agent Skills hosts other than
the documented conventions remain unverified.

## Installer snapshots

Integration is an experimental, fingerprint-gated adapter for these exact reviewed
local installer snapshots, not a general promise of upstream version support:

| Snapshot | SHA-256 |
| --- | --- |
| Original | `b68bb2432c7f948a31fb182c181295da84284337199e1f56134410ad598ce7ac` |
| Workspace patch | `1028664efa692590f525f31f93b1abcecbe4c651d11ac25741a262a4d7c933bf` |

Unknown fingerprints fail closed. Capability hints do not authorize patching.
Do not attach an installer to a public issue: locally obtained scripts may contain
account-specific credentials. Compatibility requests should include only the
fingerprint, sanitized capability result and a public download URL without tokens.
Latest upstream behavior is not certified.

## What validation proves

Automated tests use synthetic transcripts and databases. They exercise scoped
metadata attribution, bounded decompression, private transactional preparation,
unsupported-runner rejection, generated Bash syntax and synthetic mounting behavior,
upload gates, runtime integrity verification, and the CLI interface.

The official Paxel Docker consumer, project grouping, scoring, report generation
and external upload path have not been executed under this adapter. Do not treat
host syntax or synthetic tests as end-to-end certification. The tool does not alter
Paxel's scoring method. Prepared-only mode omits repository/Git metrics.

`recovery_verified` is limited to intact prepared data and agreeing aggregate
extraction/parsing observations. It cannot establish individual session identities
at the server. Upload remains unknown without official report evidence. A session
can be parsed but too short for a narrative; that is not a missing session.

Codex and Claude Code skill installation paths follow official documentation;
frontmatter is validated, but live host discovery/execution is not certified.
No universal agent compatibility or guaranteed complete recovery is claimed.
