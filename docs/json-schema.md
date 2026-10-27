# JSON contract version 1

All JSON results have `schema_version: 1`. Additive fields may appear; consumers
must ignore unknown keys. A breaking change increments this version. Values are
JSON objects, arrays, strings, integers, booleans or explicit `null`.

Inventory/diagnose:

- `workspace`: `<workspace>` unless `--show-paths`.
- `repository_count`: current workspace/direct-child Git marker count; informational,
  not evidence that a session used every repository.
- `counts`: `codex` / `antigravity`, each with integer `discovered`, `matched`,
  `eligible`, `excluded`, `unknown`, `ambiguous`, `duplicates`, `compressed`.
  Discovered counts source files, not necessarily unique sessions.
- `findings`: issue code to nonnegative file count.
- `sessions`: metadata-only entries containing pseudonymous `session_id`, `source`,
  `agent`, `source_format`, `valid`, `duplicate`, `issues`, `included`, `matched`,
  `attribution`, `confidence`, `reason`, `worktree`. `repository` appears only with
  explicit private path output. No raw remote URLs or bodies are returned.
- `pipeline`: nullable `extracted`, `parsed`, `analyzable`, `too_short`, `summarized`,
  `scored`, `uploaded`; inventory cannot observe these stages.
- diagnose adds nullable `runner` capability object and `recommendations` strings.

Rules: `EXACT_WORKSPACE_MATCH`, `DESCENDANT_PATH_MATCH`, `MULTIPLE_REPOSITORIES`,
`OUTSIDE_WORKSPACE`, `AMBIGUOUS`, `UNATTRIBUTED`. Confidence is `high`, `low` or
`unknown`. Exact/descendant matches are boundary evidence; multiple-repository
sessions can still be included only when all recorded paths lie in scope.

Preparation adds `estimated_expanded_bytes`, `estimated_output_bytes`, `disk_estimate_note`, and (after writes)
`prepared` count and `sidecar_sha256`. Included entries gain `prepared_path`, `prepared_format`, `sha256`,
`source_sha256`, `expanded_bytes`. The manifest is sanitized. Source path hashes
link entries to later inventory; no raw conversation text is stored in the manifest.

Integration returns `runner`, `bash_syntax_valid`, `prepared`, `executed: false`
and a behavioral description. Its output path is not returned in shared JSON.

Verification returns `prepared`, `integrity_ok`, `errors`, `observed` stage counts,
`log_ambiguous`, nullable `count_matches`, `recovery_verified`, and `limitation`.
`recovery_verified` is explicitly aggregate-count verification, not server identity
or upload proof. Unknown `uploaded` is always `null`.

Expected failures with `--format json` write `{"schema_version":1,"error":"..."}`
to stderr and exit 2. Argparse usage errors and `--help` remain normal argparse text.
See [sanitized example](../examples/sanitized-diagnostic.json).
