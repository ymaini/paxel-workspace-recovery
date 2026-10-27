# Codex storage

Default `~/.codex/sessions`, recursive `.jsonl` and `.jsonl.zst`. Session metadata:
`type=session_meta`, `payload.id`, `payload.cwd`, optional
`payload.git.repository_url`. Structured `turn_context.payload.cwd` adds evidence.
Never mine arbitrary prompts or shell commands for repository attribution.

The reader validates JSONL and hashes decompressed bytes while retaining no bodies.
Missing cwd yields UNATTRIBUTED even if a remote exists. Multiple differing IDs in
one file are excluded. Exact copies deduplicate by ID, agent, bytes and evidence;
conflicting copies are excluded, not silently merged.

Use `inventory --format json` first. `prepare --dry-run` reports expanded disk cost.
Codex copies preserve original JSONL bytes and file mtime. Metadata is not rewritten.
Limits and error handling: [security](../docs/security.md).
