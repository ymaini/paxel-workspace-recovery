import json
import stat

import pytest
import zstandard

from paxel_workspace.discovery.codex import parse
from paxel_workspace.integration.verification import verify
from paxel_workspace.preparation import prepare
from paxel_workspace.security import RecoveryError


def test_prepare_roundtrip(codex_session, workspace, tmp_path):
    before = codex_session.source.read_bytes()
    destination = tmp_path / "prepared"
    result = prepare([codex_session], workspace, destination)
    prepared_file = destination / result["sessions"][0]["prepared_path"]
    assert prepared_file.read_bytes() == before
    assert codex_session.source.read_bytes() == before
    assert verify(destination)["integrity_ok"]
    assert stat.S_IMODE(prepared_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert str(workspace) not in (destination / "manifest.json").read_text()


def test_dry_run(codex_session, workspace, tmp_path):
    destination = tmp_path / "prepared"
    assert prepare([codex_session], workspace, destination, dry_run=True)[
        "estimated_expanded_bytes"
    ]
    assert not destination.exists()


def test_zstd_preserves_bytes(workspace, codex_file, tmp_path):
    source = codex_file(workspace)
    raw = source.read_bytes()
    compressed = source.with_suffix(".jsonl.zst")
    compressed.write_bytes(zstandard.ZstdCompressor().compress(raw))
    destination = tmp_path / "prepared"
    result = prepare([parse(compressed)], workspace, destination)
    assert (destination / result["sessions"][0]["prepared_path"]).read_bytes() == raw


def test_existing_output(codex_session, workspace, tmp_path):
    with pytest.raises(RecoveryError):
        prepare([codex_session], workspace, tmp_path)


def test_source_changed(codex_session, workspace, tmp_path):
    codex_session.source.write_text("{}\n")
    with pytest.raises(RecoveryError, match="Source changed"):
        prepare([codex_session], workspace, tmp_path / "prepared")
    assert not (tmp_path / "prepared").exists()
    assert not list(tmp_path.glob(".paxel-prepare-*"))


def test_git_output_rejected(codex_session, workspace):
    (workspace / ".git").mkdir()
    with pytest.raises(RecoveryError, match="outside Git"):
        prepare([codex_session], workspace, workspace / "private")


def test_tamper_detected(codex_session, workspace, tmp_path):
    destination = tmp_path / "prepared"
    result = prepare([codex_session], workspace, destination)
    (destination / result["sessions"][0]["prepared_path"]).write_text("{}\n")
    assert not verify(destination)["integrity_ok"]


def test_verify_stages(codex_session, workspace, tmp_path):
    destination = tmp_path / "prepared"
    prepare([codex_session], workspace, destination)
    log = tmp_path / "run.log"
    log.write_text("Found 1 JSONL files\n1 sessions parsed\n0 analyzable\n1 too short\n")
    result = verify(destination, log)
    assert result["recovery_verified"] and result["observed"]["too_short"] == 1
    assert result["observed"]["uploaded"] is None


def test_mixed_logs_not_claimed(codex_session, workspace, tmp_path):
    destination = tmp_path / "prepared"
    prepare([codex_session], workspace, destination)
    log = tmp_path / "run.log"
    log.write_text("1 sessions parsed\n2 sessions parsed\n")
    assert verify(destination, log)["log_ambiguous"]


def test_no_log_not_recovery(codex_session, workspace, tmp_path):
    destination = tmp_path / "prepared"
    prepare([codex_session], workspace, destination)
    assert not verify(destination)["recovery_verified"]


def test_manifest_traversal(codex_session, workspace, tmp_path):
    destination = tmp_path / "prepared"
    result = prepare([codex_session], workspace, destination)
    result["sessions"][0]["prepared_path"] = "../secret.jsonl"
    (destination / "manifest.json").write_text(json.dumps(result))
    with pytest.raises(RecoveryError, match="Unsafe"):
        verify(destination)


def test_sidecar_hash_detected(codex_session, workspace, tmp_path):
    destination = tmp_path / "prepared"
    prepare([codex_session], workspace, destination)
    sidecar = destination / "transcripts/_metadata.json"
    with sidecar.open("a") as stream:
        stream.write("\n")
    assert "SIDECAR_HASH_MISMATCH" in verify(destination)["errors"]


@pytest.mark.parametrize(
    "entry", [42, None, {}, {"included": True, "prepared_path": "", "sha256": "x"}]
)
def test_invalid_manifest_entries(codex_session, workspace, tmp_path, entry):
    destination = tmp_path / "prepared"
    result = prepare([codex_session], workspace, destination)
    result["sessions"] = [entry]
    (destination / "manifest.json").write_text(json.dumps(result))
    with pytest.raises(RecoveryError):
        verify(destination)


def test_extraction_mismatch_not_success(codex_session, workspace, tmp_path):
    destination = tmp_path / "prepared"
    prepare([codex_session], workspace, destination)
    log = tmp_path / "run.log"
    log.write_text("Found 2 JSONL files\n1 sessions parsed\n")
    result = verify(destination, log)
    assert result["count_matches"] is False
    assert not result["recovery_verified"]


def test_growth_rejected_before_excess_is_written(codex_session, workspace, tmp_path):
    with codex_session.source.open("ab") as stream:
        stream.write(b"{}\n" * 1000)
    with pytest.raises(RecoveryError, match="grew"):
        prepare([codex_session], workspace, tmp_path / "prepared")
    assert not (tmp_path / "prepared").exists()
    assert not list(tmp_path.glob(".paxel-prepare-*"))
