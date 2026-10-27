"""One deterministic CLI shared by humans and agent skills."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import __version__
from .attribution import normalize
from .diagnostics import inventory, report
from .integration.detection import inspect
from .integration.patching import integrate
from .integration.verification import verify
from .preparation import prepare
from .security import MAX_BYTES, RecoveryError


def parser():
    root = argparse.ArgumentParser(
        description="Diagnose missing Paxel sessions without uploading data"
    )
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("inventory", "diagnose", "prepare", "integrate", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--format", choices=("text", "json"), default="text")
        command.add_argument("--quiet", action="store_true")
        command.add_argument(
            "--verbose", action="store_true", help="Include aggregate issue counts"
        )
        command.add_argument("--workspace", type=Path, default=Path.cwd())
        if name in ("inventory", "diagnose", "prepare"):
            command.add_argument("--codex-root", type=Path, action="append")
            command.add_argument("--gemini-root", type=Path, action="append")
            command.add_argument(
                "--max-bytes",
                type=int,
                default=MAX_BYTES,
                help="Maximum expanded bytes per transcript",
            )
            command.add_argument(
                "--show-paths",
                action="store_true",
                help="Include private source/repository paths; do not share output",
            )
        if name in ("diagnose", "integrate"):
            command.add_argument("--paxel-script", type=Path, required=name == "integrate")
        if name in ("prepare", "integrate"):
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--dry-run", action="store_true")
        if name in ("integrate", "verify"):
            command.add_argument("--prepared", type=Path, required=True)
        if name == "verify":
            command.add_argument("--manifest-sha256", help=argparse.SUPPRESS)
            command.add_argument(
                "--log", type=Path, help="One completed Paxel run log; never uploaded"
            )
    return root


def execute(args):
    workspace = normalize(str(args.workspace.expanduser().absolute()))
    if workspace is None:
        raise RecoveryError("Workspace must be a valid absolute local path.")
    if args.command == "integrate":
        return integrate(args.paxel_script, args.prepared, args.output, args.dry_run)
    if args.command == "verify":
        return verify(args.prepared, args.log, args.manifest_sha256)
    if args.max_bytes < 1:
        raise RecoveryError("--max-bytes must be positive.")
    sessions = inventory(
        args.codex_root or [Path.home() / ".codex/sessions"],
        args.gemini_root or [Path.home() / ".gemini"],
        args.max_bytes,
    )
    if args.command == "prepare":
        return prepare(sessions, workspace, args.output, args.dry_run, args.max_bytes)
    result = report(sessions, workspace, args.show_paths)
    if args.command == "diagnose":
        result["runner"] = inspect(args.paxel_script)[0] if args.paxel_script else None
        compressed = result["counts"]["codex"]["compressed"]
        result["recommendations"] = []
        if compressed:
            result["recommendations"].append(
                "Compressed files detected. Inspect runner support; prepare compatible copies."
            )
        if result["findings"].get("PARENT_WORKSPACE_SESSIONS"):
            result["recommendations"].append(
                "Parent sessions need workspace scope; remote filtering may omit them."
            )
        result["recommendations"].append(
            "Prepare --dry-run, review counts, then prepare and integrate a supported runner."
        )
    return result


def display(result):
    output = ["Paxel Workspace"]
    for agent, counts in result.get("counts", {}).items():
        output.append(
            f"{agent}: {counts['discovered']} discovered; {counts['matched']} workspace matches; "
            f"{counts['eligible']} eligible; {counts['unknown']} unknown; "
            f"{counts['excluded']} excluded"
        )
    for key in (
        "estimated_expanded_bytes",
        "estimated_output_bytes",
        "prepared",
        "integrity_ok",
        "recovery_verified",
        "count_matches",
        "bash_syntax_valid",
        "executed",
    ):
        if key in result:
            output.append(f"{key}: {result[key]}")
    if "runner" in result:
        output.append("Runner: " + json.dumps(result["runner"], sort_keys=True))
    if "observed" in result:
        output.append("Observed pipeline stages: " + json.dumps(result["observed"], sort_keys=True))
    output.extend(result.get("recommendations", []))
    output.append("Preparation is not proof of analysis. This CLI never runs or uploads reports.")
    return "\n".join(output)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = execute(args)
        if not args.quiet:
            print(json.dumps(result, indent=2) if args.format == "json" else display(result))
            if args.verbose and args.format != "json":
                print("Issues: " + json.dumps(result.get("findings", {}), sort_keys=True))
        if args.command == "verify" and (
            not result["integrity_ok"]
            or result["count_matches"] is False
            or result["log_ambiguous"]
        ):
            return 1
        return 0
    except (
        RecoveryError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.TimeoutExpired,
    ) as error:
        # Never echo underlying exception strings: JSON/OS errors can contain private input.
        message = (
            str(error)
            if isinstance(error, RecoveryError)
            else ("Cannot read input or output. Check permissions, paths, and schema; retry.")
        )
        if args.format == "json":
            print(json.dumps({"schema_version": 1, "error": message}), file=sys.stderr)
        else:
            print(f"Error: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
