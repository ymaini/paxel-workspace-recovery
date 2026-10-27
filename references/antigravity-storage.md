# Antigravity storage

Default root `~/.gemini`, surfaces `antigravity`, `antigravity-ide`,
`antigravity-cli`. Transcript:
`SURFACE/brain/UUID/.system_generated/logs/transcript.jsonl`.
Database: `SURFACE/conversations/UUID.db`.

The fixed read-only query is `SELECT data FROM trajectory_metadata_blob LIMIT 1`.
Data is binary. Observed protobuf framing uses repeated top-level field 1 workspace
descriptors (nested field 1 URI), plus top-level field 7 workspace URIs. Descriptor
field 2 can be an enclosing repository, while other nested URIs can be generated
artifacts: do not attribute every file URI as a workspace. Captured remote strings
come from bounded printable runs. Unknown framing uses conservative printable
candidates with UNSTRUCTURED_DATABASE_METADATA; eligibility requires independent
structured transcript evidence, and mixed boundaries remain excluded. Databases
with WAL are not read using immutable mode; transcript fallback is attempted.
No original database or companion file is created or modified.

Fallback reads structured `Cwd`/`cwd` fields (including double-encoded strings), then
known GENERIC workspace-access notices. Missing db/table does not discard a valid
transcript. UUID collisions with different bytes/evidence are excluded.

Preparation prepends Paxel's synthetic `antigravity_session_meta` line and appends
the untouched transcript. First prompt and model are left blank; recovery does not
need to extract prompt content. This may reduce model/prompt display fidelity.
