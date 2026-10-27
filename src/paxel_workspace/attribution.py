"""Explainable path scope; repository evidence never widens the default scope."""

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .models import Decision, Session


def normalize(value: str) -> Path | None:
    if not value or "\x00" in value or len(value) > 8192:
        return None
    if value.startswith("file:"):
        try:
            uri = urlsplit(value)
            if uri.netloc not in ("", "localhost"):
                return None
            value = unquote(uri.path)
            if "\x00" in value or uri.query or uri.fragment:
                return None
        except ValueError:
            return None
    path = Path(value)
    if not path.is_absolute():
        return None
    try:
        return Path(os.path.realpath(os.path.normpath(path)))
    except (OSError, ValueError):
        return None


def inside(path: Path, workspace: Path) -> bool:
    return path == workspace or workspace in path.parents


def git_info(path: Path) -> tuple[str, bool]:
    # Inspect git markers only. Never execute Git in transcript-controlled directories.
    for candidate in (path, *path.parents):
        marker = candidate / ".git"
        if marker.is_dir():
            return str(candidate), False
        if marker.is_file():
            return str(candidate), True
    return "", False


def repository_count(workspace: Path) -> int:
    return (
        int((workspace / ".git").exists())
        + sum(1 for child in workspace.iterdir() if child.is_dir() and (child / ".git").exists())
        if workspace.is_dir()
        else 0
    )


def attribute(session: Session, workspace: Path) -> Decision:
    workspace = normalize(str(workspace))
    if workspace is None:
        raise ValueError("Workspace must be absolute")
    paths = [normalize(value) for value in session.cwds]
    known = [path for path in paths if path is not None]
    if not known:
        return Decision(False, "UNATTRIBUTED", "unknown", "No valid recorded absolute workspace")
    matches = [inside(path, workspace) for path in known]
    if any(matches) and (not all(matches) or len(known) != len(paths)):
        return Decision(False, "AMBIGUOUS", "low", "Recorded workspaces cross selected boundary")
    if not all(matches):
        return Decision(
            False, "OUTSIDE_WORKSPACE", "high", "Recorded paths outside selected workspace"
        )
    repositories = {git_info(path)[0] for path in known} - {""}
    multiple = len(repositories) > 1 or len(session.remotes) > 1
    repo, worktree = git_info(known[0])
    if multiple:
        rule, reason = (
            "MULTIPLE_REPOSITORIES",
            "All recorded paths in scope; multiple repository evidence",
        )
    elif workspace in known:
        rule, reason = (
            "EXACT_WORKSPACE_MATCH",
            "Recorded working directory matches selected workspace",
        )
    else:
        rule, reason = (
            "DESCENDANT_PATH_MATCH",
            "Recorded working directories are descendants of workspace",
        )
    return Decision(True, rule, "high", reason, "" if multiple else repo, worktree)
