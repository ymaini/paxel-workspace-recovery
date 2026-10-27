"""Read observed Antigravity workspace fields and bounded legacy printable evidence."""

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

import zstandard

from ..attribution import normalize
from ..models import Session
from ..security import MAX_BYTES, RecoveryError, lines, path_without_symlinks
from .codex import add, files

SURFACES = ("antigravity", "antigravity-ide", "antigravity-cli")
MAX_BLOB = 2 * 1024 * 1024


def wire_fields(blob: bytes):
    """Read protobuf wire framing only; reject malformed/oversized field sets."""
    index = 0

    def varint(offset):
        value = 0
        for shift in range(0, 70, 7):
            if offset >= len(blob):
                raise ValueError("Truncated varint")
            byte = blob[offset]
            offset += 1
            value |= (byte & 127) << shift
            if not byte & 128:
                return value, offset
        raise ValueError("Invalid varint")

    fields = []
    while index < len(blob):
        tag, index = varint(index)
        number, wire = tag >> 3, tag & 7
        if not number or len(fields) >= 4096:
            raise ValueError("Invalid field count")
        if wire == 0:
            _, index = varint(index)
        elif wire in (1, 5):
            index += 8 if wire == 1 else 4
        elif wire == 2:
            size, index = varint(index)
            end = index + size
            if end > len(blob):
                raise ValueError("Truncated field")
            fields.append((number, blob[index:end]))
            index = end
        else:
            raise ValueError("Unsupported wire type")
        if index > len(blob):
            raise ValueError("Truncated fixed field")
    return fields


def workspace_uris(blob: bytes):
    # Observed snapshot schema: repeated workspace descriptors in field 1,
    # descriptor field 1 = workspace URI; field 2 = enclosing repository URI.
    # Top-level repeated field 7 mirrors workspace URIs. Other embedded file URIs
    # include generated artifacts, and are NOT workspace evidence.
    candidates = []
    structured = False
    try:
        for number, value in wire_fields(blob):
            if number == 1:
                for child_number, child_value in wire_fields(value):
                    if child_number == 1 and child_value.startswith(b"file:///"):
                        candidates.append(child_value.decode("utf-8"))
                        structured = True
            elif number == 7 and value.startswith(b"file:///"):
                candidates.append(value.decode("utf-8"))
                structured = True
    except (ValueError, UnicodeError):
        candidates = []
        structured = False
    if not structured:
        for run in re.findall(rb"[\x20-\x7e]{4,}", blob):
            candidates.extend(re.findall(r'file:///[^"\r\n<>]+', run.decode("ascii")))
    return candidates, structured


def db_metadata(path: Path) -> tuple[list[str], list[str], list[str]]:
    if not path.exists():
        return [], [], ["MISSING_DATABASE"]
    try:
        path = path_without_symlinks(path)
        # Immutable avoids SQLite creating -shm in original storage. Never use it
        # with WAL data: ignoring a live WAL would give silently stale attribution.
        wal = Path(str(path) + "-wal")
        journal = Path(str(path) + "-journal")
        if wal.exists():
            return [], [], ["ACTIVE_DATABASE_WAL"]
        if journal.exists():
            return [], [], ["ACTIVE_DATABASE_JOURNAL"]
        before = path.stat()
        with sqlite3.connect(
            f"file:{quote(str(path))}?mode=ro&immutable=1", uri=True, timeout=1
        ) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_BLOB)
            db.set_progress_handler(lambda: 1, 100000)
            kind = db.execute(
                "SELECT type FROM sqlite_schema WHERE name='trajectory_metadata_blob'"
            ).fetchone()
            if kind != ("table",):
                return [], [], ["UNREADABLE_DATABASE_OR_TABLE"]
            row = db.execute("SELECT data FROM trajectory_metadata_blob LIMIT 1").fetchone()
        after = path.stat()
        if (
            wal.exists()
            or journal.exists()
            or (before.st_size, before.st_mtime_ns)
            != (
                after.st_size,
                after.st_mtime_ns,
            )
        ):
            return [], [], ["DATABASE_CHANGED_DURING_READ"]
        if not row or not isinstance(row[0], (bytes, str)):
            return [], [], ["MALFORMED_DATABASE_METADATA"]
        blob = row[0].encode() if isinstance(row[0], str) else row[0]
        if len(blob) > MAX_BLOB:
            return [], [], ["DATABASE_METADATA_LIMIT"]
        runs = re.findall(rb"[\x20-\x7e]{4,}", blob)
        cwds, remotes = [], []
        uris, structured = workspace_uris(blob)
        for uri in uris:
            value = normalize(uri.rstrip())
            if value:
                add(cwds, str(value))
        for run in runs:
            text = run.decode("ascii")
            for remote in re.findall(r'(?:git@|https://|ssh://)[^\s"<>]+', text):
                add(remotes, remote)
        issues = [] if cwds else ["NO_DATABASE_WORKSPACE"]
        if cwds and not structured:
            issues.append("UNSTRUCTURED_DATABASE_METADATA")
        return cwds, remotes, issues
    except (OSError, sqlite3.Error, RecoveryError, ValueError):
        return [], [], ["UNREADABLE_DATABASE_OR_TABLE"]


def tool_cwds(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("Cwd", "cwd") and isinstance(child, str):
                try:
                    decoded = json.loads(child)
                    child = decoded if isinstance(decoded, str) else child
                except ValueError:
                    pass
                if normalize(child):
                    yield child
            elif isinstance(child, (dict, list)):
                yield from tool_cwds(child)
    elif isinstance(value, list):
        for child in value:
            yield from tool_cwds(child)


def parse(path: Path, db: Path, sid: str, surface: str, limit: int = MAX_BYTES):
    cwds, remotes, issues = db_metadata(db)
    if "UNSTRUCTURED_DATABASE_METADATA" in issues:
        # A printable URI may be an artifact path in an unknown schema. Require
        # independent structured transcript workspace evidence before inclusion.
        cwds = []
    session = Session("antigravity", path, sid, cwds, remotes, issues, surface=surface)
    fallback = []
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
                if not cwds:
                    for cwd in tool_cwds(record):
                        add(fallback, cwd)
                    # Official fallback for GENERIC workspace-access notices only.
                    if record.get("type") == "GENERIC":
                        text = record.get("content", record.get("text", ""))
                        if isinstance(text, str):
                            for cwd in re.findall(r"workspace\(s\):\n- ([^\n]+)", text):
                                if normalize(cwd):
                                    add(fallback, cwd)
            except (ValueError, UnicodeError, RecursionError):
                session.valid = False
                if "MALFORMED_JSONL" not in session.issues:
                    session.issues.append("MALFORMED_JSONL")
        session.digest = digest.hexdigest()
    except (OSError, RecoveryError, zstandard.ZstdError):
        session.valid = False
        session.issues.append("UNREADABLE_OR_LIMIT_EXCEEDED")
    if not cwds:
        session.cwds = fallback
        if fallback:
            session.issues.append("TRANSCRIPT_FALLBACK")
    if not session.lines:
        session.valid = False
        session.issues.append("EMPTY_TRANSCRIPT")
    return session


def discover(roots: list[Path], limit: int = MAX_BYTES):
    for root in roots:
        for surface in SURFACES:
            brain = root / surface / "brain"
            for path in files(brain, ("transcript.jsonl",)):
                relative = path.relative_to(brain)
                if len(relative.parts) != 4 or relative.parts[1:] != (
                    ".system_generated",
                    "logs",
                    "transcript.jsonl",
                ):
                    continue
                sid = relative.parts[0]
                db = root / surface / "conversations" / f"{sid}.db"
                yield parse(path, db, sid, surface, limit)
