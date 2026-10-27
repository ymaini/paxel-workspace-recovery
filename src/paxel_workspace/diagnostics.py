"""Inventory and privacy-preserving public diagnostics (schema version 1)."""

from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from .attribution import attribute, repository_count
from .discovery import antigravity, codex
from .security import MAX_BYTES, token


def inventory(codex_roots: list[Path], gemini_roots: list[Path], limit: int = MAX_BYTES):
    sessions = list(codex.discover(codex_roots, limit))
    sessions.extend(antigravity.discover(gemini_roots, limit))
    groups = defaultdict(list)
    for session in sessions:
        key = session.agent, session.session_id or session.digest or token(str(session.source))
        groups[key].append(session)
    for group in groups.values():
        evidence = {(s.digest, tuple(s.cwds), tuple(s.remotes)) for s in group if s.valid}
        if len(evidence) > 1:
            for session in group:
                session.valid = False
                session.issues.append("CONFLICTING_DUPLICATE_ID")
        elif len(group) > 1:
            # Prefer valid data, then plaintext, stable discovery order.
            ordered = sorted(group, key=lambda s: (not s.valid, s.source.suffix == ".zst"))
            for session in ordered[1:]:
                session.duplicate = True
                session.issues.append("DUPLICATE_SESSION")
    return sessions


def report(sessions, workspace: Path, show_paths: bool = False):
    rows = []
    for session in sessions:
        decision = attribute(session, workspace)
        included = decision.matched and session.valid and not session.duplicate
        row = {
            "session_id": session.session_id
            if show_paths
            else token(session.agent + (session.session_id or str(session.source))),
            "agent": session.agent,
            "source": str(session.source) if show_paths else token(str(session.source)),
            "source_format": "jsonl.zst" if session.source.suffix == ".zst" else "jsonl",
            "valid": session.valid,
            "duplicate": session.duplicate,
            "issues": sorted(set(session.issues)),
            "included": included,
            **asdict(decision),
        }
        if not show_paths:
            row.pop("repository")
        rows.append(row)
    counts = {}
    for agent in ("codex", "antigravity"):
        selected = [row for row in rows if row["agent"] == agent]
        counts[agent] = {
            "discovered": len(selected),
            "matched": sum(row["matched"] for row in selected),
            "eligible": sum(row["included"] for row in selected),
            "excluded": sum(not row["included"] for row in selected),
            "unknown": sum(row["attribution"] == "UNATTRIBUTED" for row in selected),
            "ambiguous": sum(row["attribution"] == "AMBIGUOUS" for row in selected),
            "duplicates": sum(row["duplicate"] for row in selected),
            "compressed": sum(row["source_format"] == "jsonl.zst" for row in selected),
        }
    findings = Counter(issue for row in rows for issue in row["issues"])
    findings["MISSING_RECORDED_REMOTE"] = sum(not session.remotes for session in sessions)
    findings["PARENT_WORKSPACE_SESSIONS"] = (
        sum(row["attribution"] == "EXACT_WORKSPACE_MATCH" for row in rows)
        if not (workspace / ".git").exists()
        else 0
    )
    return {
        "schema_version": 1,
        "workspace": str(workspace) if show_paths else "<workspace>",
        "repository_count": repository_count(workspace),
        "counts": counts,
        "findings": dict(sorted(findings.items())),
        "sessions": rows,
        "pipeline": {
            stage: None
            for stage in (
                "extracted",
                "parsed",
                "analyzable",
                "too_short",
                "summarized",
                "scored",
                "uploaded",
            )
        },
    }
