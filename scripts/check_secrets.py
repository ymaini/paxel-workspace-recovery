"""Offline secret scan of the exact intended source set, including reachable history.

Uses detect-secrets without credential verification/network calls. Never prints
candidate values. User must review findings locally rather than add broad ignores.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    with tempfile.TemporaryDirectory(prefix="paxel-secret-scan-") as temporary:
        root = Path(temporary)
        current = root / "current"
        current.mkdir()
        names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
        for raw in filter(None, names.split(b"\0")):
            path = Path(raw.decode())
            if path.is_symlink():
                print("Source symlink requires manual review.", file=sys.stderr)
                return 1
            if path.is_file():
                destination = current / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(path.read_bytes())
        history = root / "history"
        history.mkdir()
        for line in git("rev-list", "--objects", "--all").decode().splitlines():
            oid = line.split(" ", 1)[0]
            kind = git("cat-file", "-t", oid).decode().strip()
            if kind in ("blob", "commit", "tag"):
                (history / oid).write_bytes(git("cat-file", kind, oid))
        count = 0
        for scope in (current, history):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "detect_secrets",
                    "scan",
                    "--all-files",
                    "--no-verify",
                    str(scope),
                ],
                capture_output=True,
                check=False,
            )
            if result.returncode:
                print("Scanner failed; install .[dev] and retry.", file=sys.stderr)
                return 2
            report = json.loads(result.stdout)
            findings = sum(len(value) for value in report["results"].values())
            print(f"{scope.name}: {findings} secret candidates (values withheld)")
            count += findings
        return int(count > 0)


if __name__ == "__main__":
    raise SystemExit(main())
