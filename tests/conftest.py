import json
import sqlite3
from pathlib import Path

import pytest

from paxel_workspace.discovery.codex import parse


@pytest.fixture
def workspace(tmp_path):
    path = tmp_path / "workspace"
    path.mkdir()
    return path


@pytest.fixture
def codex_file(tmp_path):
    def make(cwd, sid="example", name="session.jsonl", remote=None, body=None):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {"type": "session_meta", "payload": {"id": sid, "cwd": str(cwd)}}
        if remote:
            meta["payload"]["git"] = {"repository_url": remote}
        path.write_text(json.dumps(meta) + "\n" + (body or ""))
        return path

    return make


@pytest.fixture
def codex_session(workspace, codex_file):
    return parse(codex_file(workspace))


@pytest.fixture
def ag_tree(tmp_path):
    def make(cwd, surface="antigravity", sid="example", database=True, blob=None, body=None):
        base = tmp_path / "gemini" / surface
        path = base / "brain" / sid / ".system_generated/logs/transcript.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(body or {"type": "TOOL_CALL", "args": {"Cwd": str(cwd)}}) + "\n")
        db = base / "conversations" / f"{sid}.db"
        if database:
            db.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE trajectory_metadata_blob (data BLOB)")
                conn.execute(
                    "INSERT INTO trajectory_metadata_blob VALUES (?)",
                    (
                        blob
                        if blob is not None
                        else b"\x00\xff" + Path(cwd).as_uri().encode() + b"\x00",
                    ),
                )
        return tmp_path / "gemini", path, db

    return make
