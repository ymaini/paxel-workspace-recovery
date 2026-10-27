"""Transactional preparation into a new private directory outside Git."""

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from .diagnostics import report
from .security import (
    MAX_BYTES,
    RecoveryError,
    atomic_write,
    chunks,
    path_without_symlinks,
    publish_directory,
    token,
)


def output_path(path: Path) -> Path:
    path = path_without_symlinks(path)
    if path.exists():
        raise RecoveryError("Output already exists. Choose a new empty destination name.")
    if not path.parent.is_dir():
        raise RecoveryError("Output parent does not exist. Create its private parent first.")
    if any((parent / ".git").exists() for parent in (path.parent, *path.parent.parents)):
        raise RecoveryError("Private outputs must be outside Git repositories.")
    return path


def prepare(sessions, workspace: Path, destination: Path, dry_run=False, limit=MAX_BYTES):
    destination = output_path(destination)
    for session in sessions:
        if destination == session.source or destination in session.source.parents:
            raise RecoveryError("Destination overlaps source storage.")
    result = report(sessions, workspace)
    result["estimated_expanded_bytes"] = sum(
        session.bytes_read
        for session, row in zip(sessions, result["sessions"], strict=True)
        if row["included"]
    )
    overhead = sum(
        4096 + 16 * sum(len(value.encode()) for value in (*session.cwds, *session.remotes))
        for session, row in zip(sessions, result["sessions"], strict=True)
        if row["included"]
    ) + 2 * len(json.dumps(result).encode())
    result["estimated_output_bytes"] = result["estimated_expanded_bytes"] + overhead
    result["disk_estimate_note"] = (
        "Conservative expanded-copy and metadata estimate; originals retained"
    )
    if dry_run:
        return result
    if shutil.disk_usage(destination.parent).free < result["estimated_output_bytes"] + 1024**2:
        raise RecoveryError("Insufficient free disk space for expanded copies and metadata.")
    stage = Path(tempfile.mkdtemp(prefix=".paxel-prepare-", dir=destination.parent))
    try:
        transcript_dir = stage / "transcripts"
        transcript_dir.mkdir(mode=0o700)
        directories = {}
        for session, row in zip(sessions, result["sessions"], strict=True):
            if not row["included"]:
                continue
            # Hash bucket keys: never use untrusted IDs, cwd or remote as path components.
            identity = json.dumps([session.cwds, session.remotes], sort_keys=True)
            bucket = f"_{session.agent}_{token(identity)}"
            directory = transcript_dir / bucket
            directory.mkdir(mode=0o700, exist_ok=True)
            relative = Path("transcripts") / bucket / f"{token(str(session.source))}.jsonl"
            target = stage / relative
            digest, source_digest = hashlib.sha256(), hashlib.sha256()
            with target.open("xb") as output:
                os.chmod(target, 0o600)
                if session.agent == "antigravity":
                    header = (
                        json.dumps(
                            {
                                "type": "antigravity_session_meta",
                                "session_id": session.session_id,
                                "cwd": session.cwds[0],
                                "git_remote": session.remotes[0]
                                if len(session.remotes) == 1
                                else "",
                                "surface": session.surface,
                                "first_prompt": "",
                                "model": "",
                            }
                        )
                        + "\n"
                    ).encode()
                    output.write(header)
                    digest.update(header)
                copied = 0
                for block in chunks(session.source, limit):
                    copied += len(block)
                    if copied > session.bytes_read:
                        raise RecoveryError("Source grew after inventory; rerun preparation.")
                    output.write(block)
                    digest.update(block)
                    source_digest.update(block)
                output.flush()
                os.fsync(output.fileno())
            if source_digest.hexdigest() != session.digest:
                raise RecoveryError("Source changed after inventory; rerun preparation.")
            os.utime(target, ns=(session.source.stat().st_mtime_ns,) * 2)
            row.update(
                {
                    "prepared_path": relative.as_posix(),
                    "prepared_format": "jsonl",
                    "sha256": digest.hexdigest(),
                    "source_sha256": session.digest,
                    "expanded_bytes": session.bytes_read,
                }
            )
            directories[bucket] = {
                "cwd": session.cwds[0],
                "git_remote": session.remotes[0] if len(session.remotes) == 1 else "",
            }
        atomic_write(
            transcript_dir / "_metadata.json",
            json.dumps(
                {
                    "version": 1,
                    "directories": directories,
                },
                indent=2,
            ).encode(),
        )
        result["sidecar_sha256"] = hashlib.sha256(
            (transcript_dir / "_metadata.json").read_bytes()
        ).hexdigest()
        result["prepared"] = sum(row["included"] for row in result["sessions"])
        # This manifest is sanitized; sidecar alone contains private recorded cwd/remote.
        atomic_write(stage / "manifest.json", json.dumps(result, indent=2).encode())
        if destination.exists():
            raise RecoveryError("Destination appeared during preparation; choose a new path.")
        publish_directory(stage, destination)
    except BaseException:
        shutil.rmtree(stage)
        raise
    return result
