"""Codex JSONL and streaming Zstandard metadata discovery."""

import hashlib
import json
import os
from pathlib import Path

import zstandard

from ..models import Session
from ..security import MAX_BYTES, RecoveryError, lines, path_without_symlinks


def files(root: Path, suffixes: tuple[str, ...]):
    if not root.exists():
        return
    root = path_without_symlinks(root)
    for parent, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(d for d in directories if not (Path(parent) / d).is_symlink())
        for name in sorted(names):
            path = Path(parent) / name
            if name.endswith(suffixes) and not path.is_symlink() and path.is_file():
                yield path


def add(target: list[str], value):
    if isinstance(value, str) and value and value not in target:
        if len(target) >= 64 or len(value) > 8192:
            raise RecoveryError("Session metadata exceeds supported limits.")
        target.append(value)


def parse(path: Path, limit: int = MAX_BYTES) -> Session:
    session = Session("codex", path)
    digest = hashlib.sha256()
    try:
        for raw in lines(path, limit):
            digest.update(raw)
            session.bytes_read += len(raw)
            session.lines += 1
            try:
                record = json.loads(raw)
                if not isinstance(record, dict):
                    raise ValueError
                payload = record.get("payload", {})
                if not isinstance(payload, dict):
                    payload = {}
                if record.get("type") == "session_meta":
                    sid = payload.get("id")
                    if isinstance(sid, str) and len(sid) <= 1024:
                        if session.session_id and session.session_id != sid:
                            session.issues.append("CONFLICTING_SESSION_IDS")
                            session.valid = False
                        session.session_id = sid
                    add(session.cwds, payload.get("cwd"))
                    git = payload.get("git", {})
                    if isinstance(git, dict):
                        add(session.remotes, git.get("repository_url"))
                elif record.get("type") == "turn_context":
                    add(session.cwds, payload.get("cwd"))
            except (ValueError, UnicodeError, RecursionError):
                session.valid = False
                if "MALFORMED_JSONL" not in session.issues:
                    session.issues.append("MALFORMED_JSONL")
        session.digest = digest.hexdigest()
    except (OSError, RecoveryError, zstandard.ZstdError):
        session.valid = False
        session.issues.append("UNREADABLE_OR_LIMIT_EXCEEDED")
    if not session.lines:
        session.valid = False
        session.issues.append("EMPTY_TRANSCRIPT")
    return session


def discover(roots: list[Path], limit: int = MAX_BYTES):
    for root in roots:
        for path in files(root, (".jsonl", ".jsonl.zst")):
            yield parse(path, limit)
