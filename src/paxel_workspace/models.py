"""Shared domain objects; no transcript bodies are retained."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    agent: str
    source: Path
    session_id: str = ""
    cwds: list[str] = field(default_factory=list)
    remotes: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    digest: str = ""
    bytes_read: int = 0
    lines: int = 0
    valid: bool = True
    duplicate: bool = False
    surface: str = ""


@dataclass
class Decision:
    matched: bool
    attribution: str
    confidence: str
    reason: str
    repository: str = ""
    worktree: bool = False
