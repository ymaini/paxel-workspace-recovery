from pathlib import Path

import pytest

from paxel_workspace.attribution import attribute, normalize
from paxel_workspace.models import Session


@pytest.mark.parametrize(
    ("relative", "matched", "rule"),
    [
        ("", True, "EXACT_WORKSPACE_MATCH"),
        ("nested/dead/path", True, "DESCENDANT_PATH_MATCH"),
        ("../workspace-old", False, "OUTSIDE_WORKSPACE"),
        ("../other", False, "OUTSIDE_WORKSPACE"),
    ],
)
def test_paths(workspace, relative, matched, rule):
    result = attribute(
        Session("codex", Path("example"), cwds=[str(workspace / relative)]), workspace
    )
    assert result.matched is matched and result.attribution == rule


def test_unknown(workspace):
    assert attribute(Session("codex", Path("example")), workspace).attribution == "UNATTRIBUTED"


def test_mixed(workspace):
    result = attribute(
        Session("codex", Path("example"), cwds=[str(workspace), "/elsewhere"]), workspace
    )
    assert not result.matched and result.attribution == "AMBIGUOUS"


def test_remote_does_not_override_path(workspace):
    result = attribute(
        Session(
            "codex", Path("example"), cwds=["/elsewhere"], remotes=["https://example.org/team/repo"]
        ),
        workspace,
    )
    assert not result.matched


def test_symlink(workspace, tmp_path):
    link = tmp_path / "alias"
    link.symlink_to(workspace)
    assert attribute(Session("codex", Path("example"), cwds=[str(link)]), workspace).matched


def test_nested_repositories(workspace):
    for name in ("repo-one", "repo-two"):
        (workspace / name / ".git").mkdir(parents=True)
    result = attribute(
        Session(
            "codex",
            Path("example"),
            cwds=[str(workspace / "repo-one"), str(workspace / "repo-two")],
        ),
        workspace,
    )
    assert result.attribution == "MULTIPLE_REPOSITORIES" and result.repository == ""


def test_parent_keeps_workspace_scope(workspace):
    (workspace / "child" / ".git").mkdir(parents=True)
    result = attribute(Session("codex", Path("example"), cwds=[str(workspace)]), workspace)
    assert result.repository == "" and result.attribution == "EXACT_WORKSPACE_MATCH"


def test_worktree(workspace):
    (workspace / ".git").write_text("gitdir: /fictional/repo/.git/worktrees/example\n")
    result = attribute(Session("codex", Path("example"), cwds=[str(workspace)]), workspace)
    assert result.worktree and result.repository == str(workspace)


@pytest.mark.parametrize("value", ["relative/path", "", "file://server/path", "/bad\x00path"])
def test_invalid_paths(value):
    assert normalize(value) is None


@pytest.mark.parametrize(
    "value", ["file://[", "file:///a%00b", "file:///a?query", "file:///a#fragment"]
)
def test_malformed_uri_is_not_workspace(value):
    assert normalize(value) is None
