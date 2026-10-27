# Contributing

Use Python 3.11+ on macOS or Linux. Keep changes focused on Codex, Antigravity,
workspace scope and safe Paxel integration.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
ruff check .
ruff format --check .
python -m build
python -m twine check dist/*
```

Tests must create fictional transcripts and SQLite databases in temporary folders.
Never commit real sessions, source projects, private filesystem paths, installer
copies, generated runner diffs or logs. Do not run external uploads in CI.

Agent adapters return `Session` metadata without retaining bodies. Add bounded
parsing, a discoverer, synthetic failure cases and privacy-preserving diagnostics.
Do not create a generic plugin framework before a concrete adapter requires it.

A new runner fingerprint requires reviewing the complete changed source, tracing
selection → extraction → Docker mounts → grouping → parsing, and confirming privacy
controls. Add a synthetic shell fixture that exercises relevant flow, rejection and
syntax checks. Do not simply append hashes to make tests pass. External containers
require separately approved end-to-end validation; report that status honestly.

Before a PR: run the checks above, review `git diff --check`, inspect package contents
and confirm no private data is present. Describe behavior changes and tested limits.
Never attach unredacted diagnostics or logs to issues. See docs/security.md.

## Release and privacy checks

Use a clean virtual environment without `--system-site-packages`. The declared dev
extra includes the offline `detect-secrets` scanner. Scan current intended source
and all reachable Git objects with:

```sh
python scripts/check_secrets.py
```

This disables online credential verification and withholds candidate values. A zero
result is not proof of no personal/customer information: manually review paths,
examples, commit authors/committers and test provenance too. Any sensitive historical
material blocks public visibility until approved remediation; never rewrite history
or force-push as a routine cleanup step.

CI uses pinned action commits, read-only default permissions, synthetic fixtures,
package validation, wheel onboarding and a macOS/Linux Python matrix. No publishing
workflow or transcript artifacts are allowed. CodeQL is staged for public repositories
with job-scoped security-event permissions; Dependabot config requires an approved
default-branch merge. Report unverified platform/agent claims explicitly.

See SECURITY.md for sensitive reports and docs/compatibility.md for supported
snapshots and validation limits. Do not publish packages, change visibility or
upload official Paxel analyses as part of a contribution without authorization.
