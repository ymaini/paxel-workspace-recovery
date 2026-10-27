# Paxel integration reference

Support is snapshot-specific. See README for accepted full hashes. Unknown hashes
allow diagnosis only; changing function names or scope anchors fails closed even
when a hash has been approved in development. Never patch by line number or globally
replace discovery patterns. Do not ship YC's original installer in this repository.

The inspected original has Codex `collect_codex_sessions` and `codex_bucket_name`,
a third `scope_cwd` argument, `.jsonl` discovery and host-extracted read-only Docker
mounts. Antigravity reads binary database metadata and prepends synthetic session
metadata. Its filtered/no-remote guard lacks workspace support. The parent-workspace
selection branch calls child-repository selection rather than workspace analysis.

Generated integration selects prepared buckets, bypasses original auto-selection,
disables other agent collectors, and uses the existing `CLAUDE_DIR:/transcripts:ro`
mount. Agent-prefixed bucket names plus `_metadata.json` carry grouping metadata to
the normal container discoverer and normalizers. Codex metadata stays byte-exact;
Antigravity receives the required synthetic header. Repository mounts/Git history
are disabled to minimize external scope. Auth/quota/privacy/upload code stays intact.

Artifacts: private `paxel-recovery.sh`, `runner.patch`, `integration.json`. Review the
patch before execution. No arguments are accepted by the generated script; no
`--all` fallback is possible. Upload gate runs before original startup. Original
Paxel pending-upload behavior remains and must be reviewed before consent.

Container consumer behavior cannot be proven from host installer syntax. Use an
explicitly approved real run, then compare complete extraction/parsing logs with
the prepared manifest. Individual session/server identity and upload require
separate official evidence. If counts differ, diagnose; never force metadata to
match a remembered number.
