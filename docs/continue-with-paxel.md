# Continue with YC Paxel

This skill prepares a recovery. To analyze those sessions and view your builder
profile, continue through [YC's official Paxel site](https://paxel.ycombinator.com/).
This project is independent and unofficial. Preparation is not proof of a successful
Paxel run, upload or report.

## 1. Set up Paxel

Open the official site and follow its current sign-in and account instructions.
Install and start a Docker runtime as directed there. Keep credentials and
personalized installer links private. Never paste tokens into an issue or agent chat.
If you only need local diagnosis, you can stop before the external run.

Before approving execution, read YC's [data-handling details](https://paxel.ycombinator.com/data-handling)
and [privacy policy](https://paxel.ycombinator.com/privacy). External analysis can
send transcript excerpts to model providers and upload processed information to YC;
it is not an offline-only operation. Review pending-upload behavior too: an old
pending payload may be replayed before a fresh analysis.

## 2. Obtain an installer without running it

Use the current installer link offered by the official site. Download it as a
private local file for inspection; do not pipe a download into Bash for this recovery
flow. No account-specific installer or token is distributed by this repository.

For the public installer URL currently linked by YC, these commands **download only**:

```sh
mkdir -p "$HOME/paxel-recovery"
chmod 700 "$HOME/paxel-recovery"
# Use a new filename; noclobber refuses an existing file.
(umask 077; set -C; curl --fail --silent --show-error --location \
  https://paxel.ycombinator.com/upload.sh > "$HOME/paxel-recovery/installer-01.sh")
```

If download fails, stop; do not run the partial file. Obtain current instructions
from the official site. A successful download does not establish compatibility.
This adapter accepts only the [reviewed snapshots](../README.md#supported-installer-snapshots).
New upstream versions, even comment-only changes, may be unsupported. Do not edit
hashes, disable guards, or run a different installer as a recovery workaround.

## 3. Diagnose, prepare and check compatibility

Replace the example workspace with the directory you intend to recover. Every
output directory must be new and outside all Git repositories. Install the CLI
using the [README](../README.md#install-the-cli) first.

```sh
paxel-workspace diagnose --workspace "$HOME/projects/my-workspace" \
  --paxel-script "$HOME/paxel-recovery/installer-01.sh"
paxel-workspace prepare --workspace "$HOME/projects/my-workspace" \
  --output "$HOME/paxel-recovery/prepared-01" --dry-run
```

Review exclusions, unknown attribution, eligible counts and space estimates. With
approval to create private copies and the runner:

```sh
paxel-workspace prepare --workspace "$HOME/projects/my-workspace" \
  --output "$HOME/paxel-recovery/prepared-01"
paxel-workspace integrate \
  --paxel-script "$HOME/paxel-recovery/installer-01.sh" \
  --prepared "$HOME/paxel-recovery/prepared-01" \
  --output "$HOME/paxel-recovery/runner-01"
paxel-workspace verify --prepared "$HOME/paxel-recovery/prepared-01"
```

Stop on any failed command. An unsupported installer can still be diagnosed, but
cannot be integrated. Review `runner.patch` and `integration.json` locally. The
runner uses prepared sessions only and disables other collectors and source-repo/
Git-history mounting. Keep the generating CLI environment installed and unchanged.

## 4. Explicitly approve and run the generated recovery copy

This is the external boundary: Docker, authentication, analysis and upload belong
to YC Paxel. Confirm the scope and its current data handling first. Approval to
prepare files does not authorize execution or upload. No automatic run is performed
by the CLI or skill.

After explicit approval, run from a trusted Bash terminal. This example refuses
to overwrite an existing log, keeps it private, and preserves a failed runner exit:

```bash
(
  umask 077
  set -o pipefail
  set -C
  : > "$HOME/paxel-recovery/run-01.log" || exit 1
  PAXEL_WORKSPACE_ALLOW_UPLOAD=YES /bin/bash \
    "$HOME/paxel-recovery/runner-01/paxel-recovery.sh" 2>&1 | tee "$HOME/paxel-recovery/run-01.log"
)
```

Follow the original runner's authentication prompts locally. Do not append options:
the generated recovery copy accepts none. If interactive authentication needs a
terminal and cannot complete through log capture, stop and seek guidance rather
than bypassing checks or exposing tokens. Treat the complete log as sensitive.
A nonzero exit is not success; inspect the private log and
[troubleshooting guide](troubleshooting.md) before retrying.

## 5. Verify locally and return to Paxel for results

After the run finishes, verify its single complete log:

```sh
paxel-workspace verify --prepared "$HOME/paxel-recovery/prepared-01" \
  --log "$HOME/paxel-recovery/run-01.log" --format json
```

Compare extracted and parsed counts with the preparation. Analyzable, too-short,
summarized and scored counts are separate stages. `null` means the stage was not
observed; `recovery_verified` does not prove per-session server inclusion or upload.
If counts disagree or the log combines multiple runs, stop and investigate.

Open [Paxel](https://paxel.ycombinator.com/) with the same account and use its report
or profile navigation to inspect the new result. Check official upload confirmation
and report status independently; this tool cannot certify them. Follow any completion
notification from YC rather than assuming a fixed processing time. For Paxel account,
Docker pipeline or report problems, use the official site's support/feedback route.
For this adapter, share only sanitized capability/error information in this repo's
issues, never installers, tokens, prepared sessions or raw logs.

The commands above are a handoff runbook, not certification of the full external
pipeline. See [compatibility limits](compatibility.md). Keep recovery outputs private;
do not commit them or remove originals during cleanup.
