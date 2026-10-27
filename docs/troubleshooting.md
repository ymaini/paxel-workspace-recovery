# Troubleshooting

| Symptom/code | Meaning and action |
| --- | --- |
| Unsupported runner SHA-256 | No patch written. Keep diagnosis; submit sanitized capability output for adapter review. Never add a hash without reviewing behavior. |
| Already integrated | Use the original supported installer and a new output directory. |
| Output already exists | Select a new name. Existing private data is never overwritten. |
| Private outputs must be outside Git | Choose a private home-directory recovery location. |
| Symlink in data path | Use a direct storage/output path. Recorded cwd symlinks are a different concern and are supported. |
| UNREADABLE_OR_LIMIT_EXCEEDED | File access, compression, decoder-window or expanded-size failure. Check permissions and format; raise `--max-bytes` only after reviewing resource risk. |
| MALFORMED_JSONL / EMPTY_TRANSCRIPT | Excluded. Repair is not attempted. Preserve original and investigate with the agent's tools. |
| CONFLICTING_SESSION_IDS | One file has multiple session identities; excluded rather than guessing. |
| DUPLICATE_SESSION | Identical session and attribution evidence already represented; one eligible copy retained. |
| CONFLICTING_DUPLICATE_ID | Same recorded ID with differing bytes/evidence. All conflicting copies excluded; inspect locally. |
| MISSING_DATABASE / UNREADABLE_DATABASE_OR_TABLE | Transcript fallback attempted. Close IDE, check permissions or storage version. |
| ACTIVE_DATABASE_JOURNAL | Rollback journal present. Close the IDE and let SQLite recover normally; never delete the journal manually. |
| ACTIVE_DATABASE_WAL | No immutable read used. Close the IDE to allow normal checkpointing, then rerun; never delete WAL manually. |
| DATABASE_CHANGED_DURING_READ | Database was active; close the IDE and retry. |
| NO_DATABASE_WORKSPACE / MALFORMED_DATABASE_METADATA | Encoding or schema unsupported; fallback may work, otherwise attribution stays unknown. |
| AMBIGUOUS | Recorded cwd evidence crosses workspace boundary. Choose intended scope explicitly; no metadata rewriting. |
| UNATTRIBUTED | No usable recorded cwd. Remotes alone are not sufficient for default path scope. |
| Source changed after inventory | Nothing published. Close active agent and rerun into a new output. |
| integrity_ok false | Do not run. Regenerate copies from originals and inspect changes. |
| log_ambiguous true | Repeated stages/runs found. Provide one complete run log; do not cherry-pick agreeing counts. |
| Count matches but no individual narrative | Check analyzable/too_short/summarized counts; short parsed sessions are not missing. |
| uploaded null | Aggregate logs cannot prove upload. Inspect official report/upload confirmation separately. |

Missing roots produce zero discovered sessions; they do not prove no history exists.
Set repeated `--codex-root` and `--gemini-root` overrides for alternate storage.
Default roots are `~/.codex/sessions` and `~/.gemini`. A Gemini root contains the
three surface directories, not an individual `brain` directory.

Expected user errors produce no stack trace and omit underlying exception messages
that could contain private data. `--verbose` prints aggregate issue counts, never
transcript bodies. Capture sanitized JSON for bug reports.

Runtime verifier import errors can indicate the CLI environment was moved/deleted.
Reinstall the CLI and regenerate integration; do not remove the integrity check.
Prepared paths containing colons or line breaks cannot be Docker bind paths: choose
a new private path and regenerate. A Bash syntax-check timeout fails without output.
