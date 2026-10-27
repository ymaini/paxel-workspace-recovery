import json
from pathlib import Path

import pytest

from paxel_workspace.cli import main
from paxel_workspace.diagnostics import report
from paxel_workspace.discovery.codex import discover, parse
from paxel_workspace.preparation import prepare
from paxel_workspace.security import MAX_LINE, RecoveryError, lines


def test_symlink_source(workspace, codex_file, tmp_path):
    source = codex_file(workspace)
    (tmp_path / "link.jsonl").symlink_to(source)
    assert len(list(discover([tmp_path]))) == 1
    assert not parse(tmp_path / "link.jsonl").valid


def test_directory_symlink(workspace, codex_file, tmp_path):
    codex_file(workspace, name="real/session.jsonl")
    (tmp_path / "alias").symlink_to(tmp_path / "real")
    assert len(list(discover([tmp_path]))) == 1


def test_output_symlink(codex_session, workspace, tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path)
    with pytest.raises(RecoveryError):
        prepare([codex_session], workspace, alias / "output")


@pytest.mark.parametrize(
    "sid", ["../../escape", "$(touch PWNED)", "a; rm -rf example", "/absolute"]
)
def test_malicious_id(workspace, codex_file, tmp_path, sid):
    session = parse(codex_file(workspace, sid=sid))
    destination = tmp_path / "prepared"
    result = prepare([session], workspace, destination)
    relative = Path(result["sessions"][0]["prepared_path"])
    assert ".." not in relative.parts and not relative.is_absolute()
    assert (destination / relative).is_file()
    assert not (tmp_path / "PWNED").exists()


def test_no_transcript_content(codex_session, workspace):
    private_body = '{"type":"event_msg","payload":{"text":"PRIVATE_SENTINEL"}}\n'
    with codex_session.source.open("a") as output:
        output.write(private_body)
    result = report([parse(codex_session.source)], workspace)
    text = json.dumps(result)
    assert "PRIVATE_SENTINEL" not in text and str(workspace) not in text


def test_line_limit(tmp_path):
    path = tmp_path / "large.jsonl"
    path.write_bytes(b"a" * (MAX_LINE + 1))
    with pytest.raises(RecoveryError):
        list(lines(path))


def test_cli_error_sanitized(tmp_path, capsys):
    result = main(["verify", "--prepared", str(tmp_path / "PRIVATE_SENTINEL"), "--format", "json"])
    assert result == 2
    output = capsys.readouterr()
    assert "PRIVATE_SENTINEL" not in output.err
    assert json.loads(output.err)["schema_version"] == 1


def test_extra_file_detected(codex_session, workspace, tmp_path):
    from paxel_workspace.integration.verification import verify

    destination = tmp_path / "prepared"
    prepare([codex_session], workspace, destination)
    (destination / "transcripts" / "extra.jsonl").write_text("{}\n")
    assert not verify(destination)["integrity_ok"]


def test_unexpected_nontranscript_file_detected(codex_session, workspace, tmp_path):
    from paxel_workspace.integration.verification import verify

    destination = tmp_path / "prepared"
    prepare([codex_session], workspace, destination)
    (destination / "transcripts/unrelated-private.txt").write_text("fictional data")
    assert "UNEXPECTED_PREPARED_FILE" in verify(destination)["errors"]


def test_prepared_symlink_rejected(codex_session, workspace, tmp_path):
    from paxel_workspace.integration.verification import verify

    destination = tmp_path / "prepared"
    prepare([codex_session], workspace, destination)
    (destination / "transcripts/alias").symlink_to(tmp_path)
    assert "SYMLINK_IN_PREPARED_TREE" in verify(destination)["errors"]


@pytest.mark.parametrize("kind", ["file", "directory", "symlink"])
def test_atomic_publish_never_replaces_existing(tmp_path, kind):
    from paxel_workspace.security import publish_directory

    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "new.txt").write_text("synthetic")
    destination = tmp_path / "destination"
    if kind == "file":
        destination.write_text("keep")
    elif kind == "directory":
        destination.mkdir()
    else:
        destination.symlink_to(stage)
    with pytest.raises((OSError, RecoveryError)):
        publish_directory(stage, destination)
    assert stage.exists() and destination.exists()
    if kind == "file":
        assert destination.read_text() == "keep"


def test_failed_publish_cleans_only_empty_reservation(tmp_path, monkeypatch):
    from paxel_workspace import security

    stage = tmp_path / "stage"
    stage.mkdir()
    destination = tmp_path / "destination"

    def fail(*args):
        raise OSError("synthetic interruption")

    monkeypatch.setattr(security.os, "replace", fail)
    with pytest.raises(OSError):
        security.publish_directory(stage, destination)
    assert stage.exists() and not destination.exists()
