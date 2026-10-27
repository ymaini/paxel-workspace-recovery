"""Verify prepared bytes and independently report observed pipeline stages."""

import json
import re
from pathlib import Path

from ..security import RecoveryError, path_without_symlinks, read_small, sha256_file

PATTERNS = {
    "parsed": r"\b(\d[\d,]*) sessions parsed\b",
    "analyzable": r"\b(\d[\d,]*) analyzable\b",
    "too_short": r"\b(\d[\d,]*) too short\b",
    "summarized": r"\b(\d[\d,]*) session summaries\b",
    "scored": r"\b(\d[\d,]*) work streams scored\b",
    "extracted": r"Found (\d[\d,]*) JSONL files\b",
}


def verify(prepared: Path, log: Path | None = None, manifest_sha256: str | None = None):
    prepared = path_without_symlinks(prepared)
    manifest_path = path_without_symlinks(prepared / "manifest.json")
    if manifest_path.stat().st_size > 64 * 1024**2:
        raise RecoveryError("Manifest exceeds supported size.")
    if manifest_sha256 and sha256_file(manifest_path) != manifest_sha256:
        raise RecoveryError("Manifest changed since runner generation; regenerate integration.")
    manifest = json.loads(read_small(manifest_path, 64 * 1024**2))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or not isinstance(manifest.get("sessions"), list)
    ):
        raise RecoveryError("Unsupported preparation manifest.")
    expected = set()
    errors = []
    for row in manifest["sessions"]:
        if not isinstance(row, dict) or not isinstance(row.get("included"), bool):
            raise RecoveryError("Malformed session entry in preparation manifest.")
        if not row.get("included"):
            continue
        if not isinstance(row.get("prepared_path"), str) or not isinstance(row.get("sha256"), str):
            raise RecoveryError("Missing prepared path or hash in manifest.")
        relative = Path(row["prepared_path"])
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or relative.parts[0] != "transcripts"
        ):
            raise RecoveryError("Unsafe prepared path in manifest.")
        path = path_without_symlinks(prepared / relative)
        if path in expected:
            raise RecoveryError("Duplicate prepared path in manifest.")
        expected.add(path)
        if not path.is_file() or sha256_file(path) != row["sha256"]:
            errors.append("MISSING_OR_CHANGED_TRANSCRIPT")
    transcript_dir = path_without_symlinks(prepared / "transcripts")
    actual = set(transcript_dir.rglob("*.jsonl"))
    if actual != expected:
        errors.append("UNEXPECTED_TRANSCRIPT_SET")
    if any(path.is_symlink() for path in transcript_dir.rglob("*")):
        errors.append("SYMLINK_IN_PREPARED_TREE")
    sidecar_path = path_without_symlinks(transcript_dir / "_metadata.json")
    if sidecar_path.stat().st_size > 16 * 1024**2:
        raise RecoveryError("Sidecar exceeds supported size.")
    if sha256_file(sidecar_path) != manifest.get("sidecar_sha256"):
        errors.append("SIDECAR_HASH_MISMATCH")
    sidecar = json.loads(read_small(sidecar_path, 16 * 1024**2))
    if not isinstance(sidecar, dict) or not isinstance(sidecar.get("directories"), dict):
        raise RecoveryError("Malformed preparation sidecar.")
    all_files = {path for path in transcript_dir.rglob("*") if path.is_file()}
    if all_files != expected | {sidecar_path}:
        errors.append("UNEXPECTED_PREPARED_FILE")
    buckets = {path.parent.name for path in expected}
    if set(sidecar.get("directories", {})) != buckets:
        errors.append("SIDECAR_BUCKET_MISMATCH")
    observed = {stage: None for stage in (*PATTERNS, "uploaded")}
    ambiguous_log = False
    if log:
        from ..security import lines

        values = {stage: [] for stage in PATTERNS}
        for raw in lines(log, 64 * 1024**2):
            line = raw.decode("utf-8", errors="replace")
            line = re.sub(r"\x1b\[[0-9;]*m", "", line)
            for stage, pattern in PATTERNS.items():
                values[stage].extend(int(n.replace(",", "")) for n in re.findall(pattern, line))
        ambiguous_log = any(len(v) > 1 for v in values.values())
        if not ambiguous_log:
            observed.update({key: value[0] if value else None for key, value in values.items()})
    expected_count = len(expected)
    return {
        "schema_version": 1,
        "prepared": expected_count,
        "integrity_ok": not errors,
        "errors": sorted(set(errors)),
        "observed": observed,
        "log_ambiguous": ambiguous_log,
        "count_matches": all(
            observed[stage] == expected_count
            for stage in ("parsed", "extracted")
            if observed[stage] is not None
        )
        if any(observed[stage] is not None for stage in ("parsed", "extracted"))
        else None,
        "recovery_verified": not errors
        and not ambiguous_log
        and observed["parsed"] == expected_count
        and observed["extracted"] == expected_count,
        "limitation": "Aggregate counts cannot prove individual session inclusion or upload",
    }
