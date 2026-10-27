import hashlib
import json

import pytest
import zstandard

from paxel_workspace.diagnostics import inventory
from paxel_workspace.discovery.codex import discover, parse


def test_plain_discovery(workspace, codex_file, tmp_path):
    codex_file(workspace)
    assert len(list(discover([tmp_path]))) == 1


def test_streaming_compressed(workspace, codex_file, tmp_path):
    path = codex_file(workspace)
    raw = path.read_bytes()
    compressed = path.with_suffix(".jsonl.zst")
    compressed.write_bytes(zstandard.ZstdCompressor().compress(raw))
    result = parse(compressed)
    assert result.valid and result.digest == hashlib.sha256(raw).hexdigest()
    assert len(list(discover([tmp_path]))) == 2


def test_no_remote(codex_session):
    assert codex_session.remotes == []
    assert codex_session.valid


def test_recorded_remote(workspace, codex_file):
    assert parse(codex_file(workspace, remote="git@example.org:team/repo.git")).remotes == [
        "git@example.org:team/repo.git"
    ]


@pytest.mark.parametrize("body", ["not json\n", "[]\n", "null\n", "\ufffd\n"])
def test_malformed(workspace, codex_file, body):
    assert not parse(codex_file(workspace, body=body)).valid


def test_empty(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.touch()
    assert "EMPTY_TRANSCRIPT" in parse(path).issues


def test_duplicate(workspace, codex_file, tmp_path):
    codex_file(workspace)
    codex_file(workspace, name="copy.jsonl")
    result = inventory([tmp_path], [])
    assert sum(s.duplicate for s in result) == 1


def test_conflict(workspace, codex_file, tmp_path):
    codex_file(workspace)
    codex_file(workspace / "other", name="copy.jsonl")
    result = inventory([tmp_path], [])
    assert all(not s.valid for s in result)


def test_missing_id(workspace, codex_file):
    path = codex_file(workspace)
    path.write_text(json.dumps({"type": "session_meta", "payload": {"cwd": str(workspace)}}) + "\n")
    assert parse(path).valid
    assert not parse(path).session_id


def test_many_lines(workspace, codex_file):
    body = '{"type":"event_msg","payload":{}}\n' * 100000
    result = parse(codex_file(workspace, body=body))
    assert result.valid and result.lines == 100001


def test_compression_limit(workspace, codex_file):
    path = codex_file(workspace)
    compressed = path.with_suffix(".jsonl.zst")
    compressed.write_bytes(zstandard.ZstdCompressor().compress(path.read_bytes()))
    assert not parse(compressed, limit=20).valid


def test_corrupt_compressed(tmp_path):
    path = tmp_path / "corrupt.jsonl.zst"
    path.write_bytes(b"not zstandard")
    assert not parse(path).valid


def test_realistic_zstd_window(workspace, codex_file):
    path = codex_file(workspace, body='{"type":"event_msg"}\n' * 200000)
    compressed = path.with_suffix(".jsonl.zst")
    compressed.write_bytes(zstandard.ZstdCompressor().compress(path.read_bytes()))
    assert parse(compressed).valid


def test_too_many_cwds_fail_closed(workspace, codex_file):
    body = "".join(
        json.dumps({"type": "turn_context", "payload": {"cwd": str(workspace / str(n))}}) + "\n"
        for n in range(70)
    )
    assert not parse(codex_file(workspace, body=body)).valid


@pytest.mark.parametrize("removed", [1, 4, 20])
def test_truncated_zstd_rejected(workspace, codex_file, removed):
    path = codex_file(workspace, body='{"type":"event_msg"}\n' * 100000)
    compressed = path.with_suffix(".jsonl.zst")
    encoded = zstandard.ZstdCompressor(write_checksum=True).compress(path.read_bytes())
    compressed.write_bytes(encoded[:-removed])
    assert not parse(compressed).valid


def test_concatenated_zstd_frames(workspace, codex_file):
    path = codex_file(workspace)
    compressed = path.with_suffix(".jsonl.zst")
    compressor = zstandard.ZstdCompressor()
    compressed.write_bytes(compressor.compress(path.read_bytes()) + compressor.compress(b"{}\n"))
    result = parse(compressed)
    assert result.valid and result.lines == 2
