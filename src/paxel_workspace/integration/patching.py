"""Minimal anchored scope branch plus locked prepared-only sources."""

import difflib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ..preparation import output_path
from ..security import (
    RecoveryError,
    atomic_write,
    path_without_symlinks,
    publish_directory,
    sha256_file,
)
from .detection import MARKER, inspect
from .verification import verify

SCOPE_ANCHOR = '''  if [ "$ALL_PROJECTS" -eq 0 ]; then
    local filtered_dir="${HOME}/.paxel/cache/filtered-transcripts-$$"'''
CALL_ANCHOR = "\nrun_docker_mode\n"


def render(text: str, prepared: Path) -> str:
    if text.count(SCOPE_ANCHOR) != 1 or text.count(CALL_ANCHOR) != 1:
        raise RecoveryError("Runner control-flow anchors changed; no patch generated.")
    # Existing collection/mount code stays intact. Only prepared buckets are exposed
    # through its /transcripts:ro mount; all agent extraction functions are inert.
    branch = '''  if [ "${PAXEL_WORKSPACE_MODE:-}" = "1" ]; then
    CLAUDE_DIR="$PAXEL_WORKSPACE_TRANSCRIPTS"
    CLAUDE_MOUNT_SCOPE="filtered"
    MOUNT_LABEL="workspace-recovery"
    selected_remote=""
    scope_cwd=""
  elif [ "$ALL_PROJECTS" -eq 0 ]; then
    local filtered_dir="${HOME}/.paxel/cache/filtered-transcripts-$$"'''
    text = text.replace(SCOPE_ANCHOR, branch, 1)
    override = f"""\n{MARKER}
# This generated copy is bound to one private preparation directory.
PAXEL_WORKSPACE_MODE=1
PAXEL_WORKSPACE_TRANSCRIPTS={shlex.quote(str(prepared / "transcripts"))}
CLAUDE_DIR="$PAXEL_WORKSPACE_TRANSCRIPTS"
TRANSCRIPT_DIR="$PAXEL_WORKSPACE_TRANSCRIPTS"
CODEX_DIR="$PAXEL_WORKSPACE_TRANSCRIPTS"
ANTIGRAVITY_DIR="$PAXEL_WORKSPACE_TRANSCRIPTS"
ALL_PROJECTS=0
PROJECT_NAME=""
# Keep source/repository mounting disabled: this run recovers transcripts only.
NO_REPO=1
collect_codex_sessions() {{ :; }}
collect_cursor_sessions() {{ :; }}
collect_opencode_sessions() {{ :; }}
collect_gemini_sessions() {{ :; }}
collect_vscode_copilot_sessions() {{ :; }}
collect_antigravity_sessions() {{ :; }}
collect_repository_git_data() {{ :; }}
count_antigravity_sessions() {{ echo 0; }}
run_docker_mode
"""
    text = text.replace(CALL_ANCHOR, override, 1)
    # Gate BEFORE the original argument parser and any original startup actions.
    split = text.index("\n") + 1
    gate = """# Prepared-only runner. Explicit upload consent required on each invocation.
if [ "$#" -ne 0 ]; then
  echo 'Recovery runner accepts no options; regenerate for another scope.' >&2
  exit 2
fi
if [ "${PAXEL_WORKSPACE_ALLOW_UPLOAD:-}" != 'YES' ]; then
  echo 'Official Paxel pipeline may upload metadata and analysis. Review its data handling.' >&2
  echo 'After explicit approval, set PAXEL_WORKSPACE_ALLOW_UPLOAD=YES to run.' >&2
  exit 2
fi
"""
    preflight = shlex.join(
        [
            sys.executable,
            "-I",
            "-m",
            "paxel_workspace.cli",
            "verify",
            "--quiet",
            "--prepared",
            str(prepared),
            "--manifest-sha256",
            sha256_file(prepared / "manifest.json"),
        ]
    )
    gate += preflight + " || exit 2\n"
    return text[:split] + gate + text[split:]


def integrate(runner: Path, prepared: Path, destination: Path, dry_run=False):
    capability, text = inspect(runner)
    if capability["already_integrated"]:
        raise RecoveryError("Already integrated; use original installer to generate a new copy.")
    if not capability["supported"]:
        raise RecoveryError(
            "Unsupported runner SHA-256; diagnose only. No speculative patch applied."
        )
    prepared = path_without_symlinks(prepared)
    if any(character in str(prepared) for character in (":", "\n", "\r")):
        raise RecoveryError(
            "Docker bind paths cannot contain colons or line breaks; choose a new path."
        )
    check = verify(prepared)
    if not check["integrity_ok"] or not check["prepared"]:
        raise RecoveryError("Preparation failed integrity checks or contains no eligible sessions.")
    destination = output_path(destination)
    patched = render(text, prepared)
    with tempfile.NamedTemporaryFile(suffix=".sh") as temporary:
        temporary.write(patched.encode())
        temporary.flush()
        bash = shutil.which("bash", path=os.defpath)
        if not bash:
            raise RecoveryError("Bash is required for integration; install it and retry.")
        syntax = subprocess.run(
            [bash, "-n", temporary.name],
            capture_output=True,
            check=False,
            env={"PATH": os.defpath},
            stdin=subprocess.DEVNULL,
            timeout=15,
        )
    if syntax.returncode:
        raise RecoveryError("Generated runner failed Bash syntax validation; no outputs written.")
    diff = "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile="original-installer",
            tofile="prepared-only-runner",
        )
    )
    metadata = {
        "schema_version": 1,
        "runner": capability,
        "bash_syntax_valid": True,
        "prepared": check["prepared"],
        "executed": False,
        "behavior": "Prepared /transcripts:ro mount; other collectors and repo mounts disabled",
    }
    if not dry_run:
        stage = Path(tempfile.mkdtemp(prefix=".paxel-integrate-", dir=destination.parent))
        try:
            atomic_write(stage / "paxel-recovery.sh", patched.encode())
            atomic_write(stage / "runner.patch", diff.encode())
            atomic_write(stage / "integration.json", json.dumps(metadata, indent=2).encode())
            publish_directory(stage, destination)
        except BaseException:
            shutil.rmtree(stage)
            raise
    return metadata
