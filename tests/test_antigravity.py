import sqlite3

import pytest

from paxel_workspace.diagnostics import inventory
from paxel_workspace.discovery.antigravity import db_metadata, discover, parse


def test_database(workspace, ag_tree):
    root, path, db = ag_tree(workspace)
    result = parse(path, db, "example", "antigravity")
    assert result.valid and result.cwds == [str(workspace)]
    assert len(list(discover([root]))) == 1


def test_missing_db_fallback(workspace, ag_tree):
    _, path, db = ag_tree(workspace, database=False)
    result = parse(path, db, "example", "antigravity")
    assert result.cwds == [str(workspace)]
    assert "MISSING_DATABASE" in result.issues


def test_double_encoded_cwd(workspace, ag_tree):
    _, path, db = ag_tree(workspace, database=False, body={"args": {"Cwd": f'"{workspace}"'}})
    assert parse(path, db, "example", "antigravity").cwds == [str(workspace)]


def test_missing_table(tmp_path):
    db = tmp_path / "metadata.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE unrelated (data BLOB)")
    assert "UNREADABLE_DATABASE_OR_TABLE" in db_metadata(db)[2]


def test_invalid_db(tmp_path):
    db = tmp_path / "bad.db"
    db.write_bytes(b"not sqlite")
    assert "UNREADABLE_DATABASE_OR_TABLE" in db_metadata(db)[2]


@pytest.mark.parametrize("blob", [b"\xff\xfe\x01", b"", b"garbage", b"file://remotehost/path"])
def test_malformed_metadata(workspace, ag_tree, blob):
    _, _, db = ag_tree(workspace, blob=blob)
    assert not db_metadata(db)[0]


def test_uri_escaping(workspace, ag_tree):
    path = workspace / "project name"
    _, _, db = ag_tree(path)
    assert db_metadata(db)[0] == [str(path)]


def test_remote(workspace, ag_tree):
    blob = workspace.as_uri().encode() + b"\x00git@example.org:team/repo.git\x00"
    _, _, db = ag_tree(workspace, blob=blob)
    assert db_metadata(db)[1] == ["git@example.org:team/repo.git"]


def test_surfaces_dedup(workspace, ag_tree):
    root, _, _ = ag_tree(workspace)
    ag_tree(workspace, surface="antigravity-ide")
    result = inventory([], [root])
    assert len(result) == 2 and sum(s.duplicate for s in result) == 1


def test_database_readonly(workspace, ag_tree):
    _, _, db = ag_tree(workspace)
    original = db.read_bytes()
    db_metadata(db)
    assert original == db.read_bytes()


def test_multi_workspace_blob(workspace, ag_tree):
    blob = workspace.as_uri().encode() + b"\x00file:///elsewhere\x00"
    _, _, db = ag_tree(workspace, blob=blob)
    assert len(db_metadata(db)[0]) == 2


def test_structured_workspace_not_repository_or_artifact(workspace, ag_tree):
    def field(number, value):
        # This fixture uses short strings so one-byte lengths suffice.
        size = len(value)
        encoded = bytearray()
        while size > 127:
            encoded.append((size & 127) | 128)
            size >>= 7
        encoded.append(size)
        return bytes([number << 3 | 2]) + bytes(encoded) + value

    uri = workspace.as_uri().encode()
    descriptor = field(1, uri) + field(2, b"file:///outside-repository-parent")
    blob = field(1, descriptor) + field(7, uri) + field(10, b"file:///private-generated-artifact")
    _, _, db = ag_tree(workspace, blob=blob)
    paths, _, issues = db_metadata(db)
    assert paths == [str(workspace)]
    assert not issues


def test_active_wal_falls_back(workspace, ag_tree):
    _, path, db = ag_tree(workspace)
    from pathlib import Path

    Path(str(db) + "-wal").write_bytes(b"synthetic active WAL")
    result = parse(path, db, "example", "antigravity")
    assert "ACTIVE_DATABASE_WAL" in result.issues
    assert result.cwds == [str(workspace)]


def test_rollback_journal_falls_back(workspace, ag_tree):
    from pathlib import Path

    _, path, db = ag_tree(workspace)
    Path(str(db) + "-journal").touch()
    result = parse(path, db, "example", "antigravity")
    assert "ACTIVE_DATABASE_JOURNAL" in result.issues
    assert result.cwds == [str(workspace)]


def test_view_is_not_accepted_as_metadata_table(tmp_path):
    db = tmp_path / "view.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE VIEW trajectory_metadata_blob AS SELECT 'file:///outside' AS data")
    assert db_metadata(db)[0] == []
    assert "UNREADABLE_DATABASE_OR_TABLE" in db_metadata(db)[2]


def test_unknown_blob_schema_requires_transcript_evidence(workspace, ag_tree):
    _, path, db = ag_tree(
        workspace, blob=b"\xfffile:///untrusted-reference\x00", body={"type": "USER_INPUT"}
    )
    result = parse(path, db, "example", "antigravity")
    assert not result.cwds and "UNSTRUCTURED_DATABASE_METADATA" in result.issues
