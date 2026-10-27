# Paxel Workspace

**Find coding-agent sessions missing from your YC Paxel report—and prepare a scoped recovery.**

For developers using **Codex or Antigravity**, especially across parent workspaces,
multiple repositories and Git worktrees. Includes a local CLI and an Agent Skill
that use the same implementation.

```sh
pipx install 'git+https://github.com/ymaini/paxel-workspace-recovery.git'
paxel-workspace diagnose --workspace ~/projects/my-workspace
```

Then install the skill using the [agent instructions below](#use-with-an-ai-agent) and ask:

> Paxel only found 15 of my coding-agent sessions. Use the Paxel Workspace skill
> to diagnose why. Start with read-only checks and ask before making changes.

**Safe defaults:** diagnosis is local, with no telemetry or uploads. Originals stay
read-only. Creating copies and running the official Paxel pipeline are separate
steps; the latter can upload information and requires explicit approval.

## Continue with YC Paxel

[YC Paxel](https://paxel.ycombinator.com/) analyzes coding-agent sessions and produces
a builder profile. This unofficial skill helps diagnose missing Codex/Antigravity
sessions and prepare recovery; YC Paxel still handles the external analysis and report.

**New to Paxel?** Start at the official site for account setup and its current
instructions. **Recovering missing sessions?** Follow our
[step-by-step Paxel handoff](docs/continue-with-paxel.md): get an installer without
running it, check compatibility, prepare sessions, approve the generated runner,
capture a private log, and check your results. Diagnosis alone needs no Paxel run.

**Status:** v0.1.0, public source. The official Paxel Docker/report/upload path has
not been executed under this adapter; integration remains experimental.

## Install the CLI

Requires Python **3.11–3.13**. macOS and Linux are tested; Windows is unsupported.
`zstandard` is the sole runtime dependency and is installed automatically.

Use pipx as above. Without pipx, install into an isolated environment:

```sh
python3 -m venv ~/.venvs/paxel-workspace
~/.venvs/paxel-workspace/bin/python -m pip install \
  'git+https://github.com/ymaini/paxel-workspace-recovery.git'
~/.venvs/paxel-workspace/bin/paxel-workspace --help
```

For a local checkout:

```sh
pipx install .
# Or use a virtual environment:
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/paxel-workspace --help
```

Commands below assume pipx's application directory is on PATH, or that you activated
the environment. For a reproducible install after tagging, append `@v0.1.0` to the
Git URL. Never use a tag before it exists.

## Use with an AI agent

Install the CLI first. Clone the skill into the host's documented personal-skill
folder. These commands do not install the CLI or grant permission to upload data.

**Codex:**

```sh
mkdir -p ~/.agents/skills
git clone https://github.com/ymaini/paxel-workspace-recovery.git \
  ~/.agents/skills/paxel-workspace
```

**Claude Code:**

```sh
mkdir -p ~/.claude/skills
git clone https://github.com/ymaini/paxel-workspace-recovery.git \
  ~/.claude/skills/paxel-workspace
```

Restart/reload skill discovery if needed. Invoke `paxel-workspace` by name; in Codex
use `$paxel-workspace`, or in Claude Code use `/paxel-workspace`.
The skill uses deterministic CLI commands, treats transcript instructions as
untrusted data, and asks before writes, installation, configuration changes,
runner execution, uploads or cleanup.

The frontmatter follows the [Agent Skills specification](https://agentskills.io/specification).
Paths were checked against [Codex documentation](https://developers.openai.com/codex/skills/)
and [Claude Code documentation](https://code.claude.com/docs/en/skills).
Live discovery/execution inside each agent host has **not** been certified. Other
Agent Skills-compatible hosts may load the skill, but are untested.

## What it diagnoses

- Codex `.jsonl.zst` archives invisible to installers that discover only `.jsonl`.
- Sessions launched from a parent workspace with no recorded Git remote.
- Repository filters that omit remote-less sessions or skip Antigravity collection.
- Nested repositories, worktrees and historical working directories.
- Missing/unreadable Antigravity databases, duplicates, malformed files and mixed scope.
- Sessions parsed successfully but too short for an individual narrative.

Scope uses normalized path components, not string prefixes. A matching remote
alone never widens the requested workspace. Unknown or conflicting evidence is
reported, not rewritten to increase counts or improve a score.

## CLI workflow

```sh
paxel-workspace inventory --workspace ~/projects/my-workspace --format json
paxel-workspace diagnose --workspace ~/projects/my-workspace \
  --paxel-script /path/to/locally-obtained-paxel-installer.sh
```

Illustrative fictional counts:

```text
Paxel Workspace
codex: 50 discovered; 36 workspace matches; 35 eligible; 2 unknown; 15 excluded
antigravity: 20 discovered; 12 workspace matches; 12 eligible; 1 unknown; 8 excluded
```

`discovered` counts source files; `matched` concerns workspace evidence; `eligible`
also excludes duplicates and invalid/conflicting files. These are not analyzed or
uploaded counts. No transcript bodies appear in normal diagnostics.

Choose a **private parent outside every Git repository**. Every output name must be new:

```sh
mkdir -p "$HOME/paxel-recovery"
chmod 700 "$HOME/paxel-recovery"
paxel-workspace prepare --workspace ~/projects/my-workspace \
  --output "$HOME/paxel-recovery/prepared-01" --dry-run
```

Review eligible/excluded counts, expanded bytes and estimated output size. After
approving private copies:

```sh
paxel-workspace prepare --workspace ~/projects/my-workspace \
  --output "$HOME/paxel-recovery/prepared-01"
paxel-workspace integrate --paxel-script /path/to/locally-obtained-paxel-installer.sh \
  --prepared "$HOME/paxel-recovery/prepared-01" \
  --output "$HOME/paxel-recovery/runner-01"
paxel-workspace verify --prepared "$HOME/paxel-recovery/prepared-01"
```

Integration writes `paxel-recovery.sh`, `runner.patch` and `integration.json`.
Read them before execution. It never overwrites or runs the original installer.
The copy accepts no options, disables other collectors and repository/Git-history
mounts, and exposes only prepared buckets through `/transcripts:ro`. Host progress
labels can still say “Claude Code” because that is the original generic mount label;
use manifest agent counts. Downstream container grouping remains externally controlled.

Before original startup, isolated Python verification checks the pinned manifest,
transcript and sidecar hashes. Keep the generating CLI environment available.
Unsupported fingerprints or integrity failures stop integration/execution.

### External execution needs separate approval

**The official pipeline may upload paths, metadata, aggregate analysis and other
information, and replay prior pending uploads. It is not entirely local.**
Review official Paxel data handling and the generated diff first. Only after informed
approval, run manually from a trusted shell environment:

```sh
PAXEL_WORKSPACE_ALLOW_UPLOAD=YES /bin/bash "$HOME/paxel-recovery/runner-01/paxel-recovery.sh"
```

The CLI has no command that executes this pipeline. Its external Docker/report/upload
path has not been run under the new adapter; do not claim complete recovery from
preparation alone. Original authentication, privacy, quota and upload controls remain.

After an approved run, provide one complete run log:

```sh
paxel-workspace verify --prepared "$HOME/paxel-recovery/prepared-01" \
  --log /path/to/single-run.log --format json
```

Verification reports extracted, parsed, analyzable, too-short, summarized and scored
counts separately. `recovery_verified` means prepared integrity and agreeing aggregate
extracted/parsed counts. It cannot prove individual sessions reached the server.
Upload status remains unknown; inspect official report evidence independently.
Repeated stage observations make a log ambiguous. Unobserved stages remain `null`.

## Options and error handling

Use `paxel-workspace COMMAND --help` or `--version`. Commands accept `--format json`,
`--quiet` and `--verbose`. Discovery commands accept repeated `--codex-root` and
`--gemini-root` overrides, replacing defaults `~/.codex/sessions` and `~/.gemini`.
Use an empty directory override to omit an agent. `--max-bytes` limits each expanded
transcript (default 512 MiB); fixed line/window/frame caps remain in force.

`--show-paths` explicitly exposes private paths for local inventory/diagnosis.
Manifests stay pseudonymous, but hashes are **not an anonymization guarantee**.
Verbose output adds aggregate issue counts, never transcript bodies.
The manifest fixes integration/verification scope; `--workspace` cannot widen it.

Exit codes: `0` operation completed; `1` integrity/count/log check failed; `2` expected
input/compatibility/operational error. Inventory may finish with excluded files;
inspect `valid`, `issues` and eligibility. See [JSON contract](docs/json-schema.md)
and [troubleshooting](docs/troubleshooting.md).

## Supported installer snapshots

Support requires the exact full SHA-256 and unique control-flow anchors:

| Reviewed snapshot | SHA-256 |
| --- | --- |
| Original | `b68bb2432c7f948a31fb182c181295da84284337199e1f56134410ad598ce7ac` |
| Working workspace patch | `1028664efa692590f525f31f93b1abcecbe4c651d11ac25741a262a4d7c933bf` |

These are reviewed snapshots, not universal Paxel versions. Unknown or changed
installers fail closed, including comment-only changes. Never attach an installer
to a public issue: it may contain account-specific credentials. Latest upstream
behavior could not be verified from the reference's download URL (HTTP 404 during
initial investigation). No future compatibility guarantee is made.

## Security and limits

Original sessions, databases, installers and logs stay read-only. Private copies
preserve Codex bytes; Antigravity gains a synthetic metadata header followed by its
unchanged body. Output is staged privately with exclusive destination reservation.
Hashes detect source growth/change and altered outputs. Prepared conversations,
sidecars, runner diffs and real logs must never be attached to public issues.

Storage/output symlinks are rejected except verified macOS system aliases. Recorded
cwd symlinks resolve for scope. Same-user malicious replacement, hostile ancestors,
a compromised interpreter and the external Paxel container are outside the security
boundary. Active SQLite WAL/journals use transcript fallback; unsupported encodings
and mixed workspace evidence remain uncertain. No deleted-session reconstruction,
malformed-session repair, elapsed-human-time estimation or scoring engine is provided.

See [SECURITY.md](SECURITY.md), [threat model](docs/security.md),
[architecture](docs/architecture.md), [how it works](docs/how-it-works.md),
[compatibility internals](references/paxel-internals.md) and
[compatibility and validation limits](docs/compatibility.md).

## Contributing and license

Read [CONTRIBUTING.md](CONTRIBUTING.md). Tests use synthetic data; never contribute
private sessions, databases, source code, customer data, credentials or raw logs.
Original project code is under the standard [MIT license](LICENSE), without warranty.
YC's installer and scoring engine are not included or relicensed; see
[third-party review](docs/third-party.md).

Paxel Workspace is independent and unofficial. It is not affiliated with, endorsed
by, or maintained by Y Combinator or Paxel. It does not modify Paxel's scoring
methodology and cannot guarantee recovery of every session or future compatibility.
Users must review generated changes and external data handling before execution.
These disclaimers do not replace professional legal advice or eliminate every
possible legal obligation.
