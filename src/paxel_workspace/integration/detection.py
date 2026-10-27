"""Known installer snapshots, not guessed release versions."""

import hashlib
from pathlib import Path

from ..security import RecoveryError, path_without_symlinks, read_small

SUPPORTED = {
    "b68bb2432c7f948a31fb182c181295da84284337199e1f56134410ad598ce7ac": "inspected-original",
    "1028664efa692590f525f31f93b1abcecbe4c651d11ac25741a262a4d7c933bf": "inspected-workspace-patch",
}
MARKER = "# paxel-workspace integration v1"


def inspect(path: Path):
    path = path_without_symlinks(path)
    if path.stat().st_size > 2 * 1024**2:
        raise RecoveryError("Runner exceeds supported size limit.")
    data = read_small(path, 2 * 1024**2)
    digest = hashlib.sha256(data).hexdigest()
    text = data.decode("utf-8")
    return {
        "sha256": digest,
        "supported": digest in SUPPORTED,
        "snapshot": SUPPORTED.get(digest, "unknown"),
        "already_integrated": MARKER in text,
        "compressed_discovery": '"*.jsonl.zst"' in text,
        "native_codex_workspace_parameter": 'local scope_cwd="${3:-}"' in text,
        "antigravity_workspace_guard": (
            'if [ "${CLAUDE_MOUNT_SCOPE:-all}" = "filtered" ] '
            '&& [ -z "${selected_remote:-}" ] && [ -z "${scope_cwd:-}" ]; then\n'
            '      echo "  Antigravity: skipped' in text
        ),
        "note": "Capabilities are structural hints, not proof of runtime support",
    }, text
