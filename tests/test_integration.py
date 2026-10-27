import hashlib
import os
import subprocess

import pytest

from paxel_workspace.integration import detection
from paxel_workspace.integration.detection import inspect
from paxel_workspace.integration.patching import integrate
from paxel_workspace.preparation import prepare
from paxel_workspace.security import RecoveryError

# Original synthetic shell, not copied YC implementation.
RUNNER = """#!/bin/bash
run_docker_mode() {
  if [ "$ALL_PROJECTS" -eq 0 ]; then
    local filtered_dir="${HOME}/.paxel/cache/filtered-transcripts-$$"
    echo original-selection
  fi
  docker_args=(-v "${CLAUDE_DIR}:/transcripts:ro")
  printf '%s\\n' "${docker_args[@]}"
  collect_codex_sessions /unused
  collect_antigravity_sessions /unused
}
collect_codex_sessions() { echo unexpected-codex-extraction; }
collect_antigravity_sessions() { echo unexpected-antigravity-extraction; }
run_docker_mode
"""


@pytest.fixture
def integration_inputs(codex_session, workspace, tmp_path, monkeypatch):
    prepared = tmp_path / "prepared"
    prepare([codex_session], workspace, prepared)
    runner = tmp_path / "runner.sh"
    runner.write_text(RUNNER)
    digest = hashlib.sha256(runner.read_bytes()).hexdigest()
    monkeypatch.setitem(detection.SUPPORTED, digest, "synthetic-test-only")
    return runner, prepared, tmp_path / "integration"


def test_supported_and_mount(integration_inputs):
    runner, prepared, output = integration_inputs
    original = runner.read_bytes()
    assert integrate(runner, prepared, output)["bash_syntax_valid"]
    patched = output / "paxel-recovery.sh"
    result = subprocess.run(
        ["bash", str(patched)],
        capture_output=True,
        text=True,
        env={**os.environ, "PAXEL_WORKSPACE_ALLOW_UPLOAD": "YES"},
        check=False,
    )
    assert result.returncode == 0
    assert f"{prepared}/transcripts:/transcripts:ro" in result.stdout
    assert "original-selection" not in result.stdout
    assert "unexpected" not in result.stdout
    assert runner.read_bytes() == original
    assert (output / "runner.patch").exists()


def test_consent_gate(integration_inputs):
    runner, prepared, output = integration_inputs
    integrate(runner, prepared, output)
    result = subprocess.run(
        ["bash", str(output / "paxel-recovery.sh")],
        capture_output=True,
        env={"PATH": os.environ["PATH"]},
        check=False,
    )
    assert result.returncode == 2 and not result.stdout


@pytest.mark.parametrize("argument", ["--all", "--project", "--resume-pending", "--since"])
def test_options_rejected(integration_inputs, argument):
    runner, prepared, output = integration_inputs
    integrate(runner, prepared, output)
    result = subprocess.run(
        ["bash", str(output / "paxel-recovery.sh"), argument], capture_output=True, check=False
    )
    assert result.returncode == 2


def test_unsupported(integration_inputs):
    runner, prepared, output = integration_inputs
    runner.write_text(RUNNER + "# drift\n")
    with pytest.raises(RecoveryError, match="Unsupported"):
        integrate(runner, prepared, output)
    assert not output.exists()


@pytest.mark.parametrize(
    "old,new",
    [
        ("run_docker_mode", "renamed_main"),
        ("local filtered_dir=", "local renamed_dir="),
    ],
)
def test_changed_anchors_fail(integration_inputs, monkeypatch, old, new):
    runner, prepared, output = integration_inputs
    runner.write_text(RUNNER.replace(old, new))
    monkeypatch.setitem(
        detection.SUPPORTED, hashlib.sha256(runner.read_bytes()).hexdigest(), "test"
    )
    with pytest.raises(RecoveryError, match="anchors changed"):
        integrate(runner, prepared, output)


def test_repeat_and_already_patched(integration_inputs):
    runner, prepared, output = integration_inputs
    integrate(runner, prepared, output)
    with pytest.raises(RecoveryError):
        integrate(runner, prepared, output)
    patched = output / "paxel-recovery.sh"
    assert inspect(patched)[0]["already_integrated"]
    with pytest.raises(RecoveryError, match="Already integrated"):
        integrate(patched, prepared, output.parent / "again")


def test_dry_run(integration_inputs):
    runner, prepared, output = integration_inputs
    assert integrate(runner, prepared, output, dry_run=True)["bash_syntax_valid"]
    assert not output.exists()


def test_syntax_failure(integration_inputs, monkeypatch):
    runner, prepared, output = integration_inputs
    runner.write_text(RUNNER.replace("echo original-selection", "if then"))
    monkeypatch.setitem(
        detection.SUPPORTED, hashlib.sha256(runner.read_bytes()).hexdigest(), "test"
    )
    with pytest.raises(RecoveryError, match="syntax"):
        integrate(runner, prepared, output)
    assert not output.exists()


def test_runtime_preflight_rejects_changed_manifest(integration_inputs):
    runner, prepared, output = integration_inputs
    integrate(runner, prepared, output)
    with (prepared / "manifest.json").open("a") as stream:
        stream.write("\n")
    result = subprocess.run(
        ["bash", str(output / "paxel-recovery.sh")],
        capture_output=True,
        env={**os.environ, "PAXEL_WORKSPACE_ALLOW_UPLOAD": "YES"},
        check=False,
    )
    assert result.returncode == 2 and not result.stdout


def test_shell_metacharacters_in_prepared_path(integration_inputs):
    runner, prepared, output = integration_inputs
    unusual = prepared.parent / "prepared ' ; $(touch PWNED)"
    prepared.rename(unusual)
    integrate(runner, unusual, output)
    result = subprocess.run(
        ["bash", str(output / "paxel-recovery.sh")],
        capture_output=True,
        text=True,
        env={**os.environ, "PAXEL_WORKSPACE_ALLOW_UPLOAD": "YES"},
        check=False,
    )
    assert result.returncode == 0
    assert f"{unusual}/transcripts:/transcripts:ro" in result.stdout
    from pathlib import Path

    assert not Path("PWNED").exists()


def test_runtime_preflight_ignores_project_python_shadow(integration_inputs, tmp_path):
    runner, prepared, output = integration_inputs
    integrate(runner, prepared, output)
    shadow = tmp_path / "paxel_workspace"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("raise SystemExit(99)\n")
    result = subprocess.run(
        ["bash", str(output / "paxel-recovery.sh")],
        cwd=tmp_path,
        env={**os.environ, "PAXEL_WORKSPACE_ALLOW_UPLOAD": "YES", "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0


def test_syntax_checker_ignores_bash_env(integration_inputs, tmp_path, monkeypatch):
    runner, prepared, output = integration_inputs
    startup = tmp_path / "startup"
    sentinel = tmp_path / "UNEXPECTED"
    startup.write_text(f"touch '{sentinel}'\n")
    monkeypatch.setenv("BASH_ENV", str(startup))
    integrate(runner, prepared, output)
    assert not sentinel.exists()


@pytest.mark.parametrize("suffix", [":colon", "\nnewline", "\rcarriage"])
def test_invalid_docker_bind_path(integration_inputs, suffix):
    runner, prepared, output = integration_inputs
    unusual = prepared.parent / (prepared.name + suffix)
    prepared.rename(unusual)
    with pytest.raises(RecoveryError, match="Docker bind paths"):
        integrate(runner, unusual, output)
    assert not output.exists()
