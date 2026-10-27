import json
import socket

import pytest

from paxel_workspace.cli import main


@pytest.mark.parametrize("command", ["inventory", "diagnose", "prepare", "integrate", "verify"])
def test_subcommand_help(command):
    with pytest.raises(SystemExit) as result:
        main([command, "--help"])
    assert result.value.code == 0


def test_version(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--version"])
    assert result.value.code == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_diagnosis_is_local(workspace, tmp_path, capsys, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network prohibited")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert (
        main(
            [
                "diagnose",
                "--workspace",
                str(workspace),
                "--codex-root",
                str(tmp_path / "codex"),
                "--gemini-root",
                str(tmp_path / "gemini"),
                "--format",
                "json",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["schema_version"] == 1
    assert result["counts"]["codex"]["discovered"] == 0


def test_bad_limit_is_actionable(tmp_path, capsys):
    assert main(["inventory", "--max-bytes", "0", "--format", "json"]) == 2
    result = json.loads(capsys.readouterr().err)
    assert "positive" in result["error"]
