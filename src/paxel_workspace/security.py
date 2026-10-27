"""Bounded reads, no-follow opens, and private atomic output."""

import contextlib
import hashlib
import io
import os
import stat
import sys
import tempfile
from pathlib import Path

import zstandard

MAX_BYTES = 512 * 1024 * 1024
MAX_LINE = 8 * 1024 * 1024


class RecoveryError(Exception):
    """Expected error safe to display without private input."""


def path_without_symlinks(path: Path) -> Path:
    path = Path(os.path.abspath(path.expanduser()))
    # macOS system aliases are trusted platform paths, not user-data links.
    if sys.platform == "darwin":
        for alias in (Path("/tmp"), Path("/var")):  # noqa: S108 - trusted OS aliases
            if path == alias or alias in path.parents:
                expected = Path("/private") / alias.name
                if alias.is_symlink() and alias.resolve() == expected:
                    path = expected / path.relative_to(alias)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RecoveryError("Symlink in data path; choose a direct, non-symlink path.")
    return path


def validate_zstd_frames(raw):
    """Validate frame boundaries: stream_reader alone can accept truncated tails.

    Zstandard block headers encode last/type/size in three little-endian bytes.
    Decode payloads with libzstd; this pass only ensures complete framing and
    enforces windows before any decoder allocation. Skippable frames are unsupported.
    """
    size = os.fstat(raw.fileno()).st_size
    if size > MAX_BYTES:
        raise RecoveryError("Compressed source exceeds supported size.")
    frames = 0
    while raw.tell() < size:
        start = raw.tell()
        header = raw.read(18)
        if header[:4] != b"\x28\xb5\x2f\xfd":
            raise RecoveryError("Unsupported or incomplete Zstandard frame.")
        params = zstandard.get_frame_parameters(header)
        if params.window_size > 128 * 1024 * 1024:
            raise RecoveryError("Zstandard decoder window exceeds 128 MiB.")
        raw.seek(start + zstandard.frame_header_size(header))
        while True:
            block_header = raw.read(3)
            if len(block_header) != 3:
                raise RecoveryError("Truncated Zstandard block header.")
            packed = int.from_bytes(block_header, "little")
            last, kind, block_size = packed & 1, (packed >> 1) & 3, packed >> 3
            if kind == 3:
                raise RecoveryError("Reserved Zstandard block type.")
            end = raw.tell() + (1 if kind == 1 else block_size)
            if end > size:
                raise RecoveryError("Truncated Zstandard block payload.")
            raw.seek(end)
            if last:
                break
        if params.has_checksum:
            if len(raw.read(4)) != 4:
                raise RecoveryError("Truncated Zstandard checksum.")
        frames += 1
        if frames > 1024:
            raise RecoveryError("Too many concatenated Zstandard frames.")
    if not frames:
        raise RecoveryError("Empty compressed source.")
    raw.seek(0)


@contextlib.contextmanager
def source_stream(path: Path):
    path = path_without_symlinks(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as raw:
        if not stat.S_ISREG(os.fstat(raw.fileno()).st_mode):
            raise RecoveryError("Source is not a regular file.")
        if path.name.endswith(".zst"):
            validate_zstd_frames(raw)
            decoder = zstandard.ZstdDecompressor(max_window_size=128 * 1024 * 1024)
            with decoder.stream_reader(raw, read_across_frames=True) as stream:
                yield io.BufferedReader(stream)
        else:
            yield raw


def chunks(path: Path, limit: int = MAX_BYTES):
    total = 0
    with source_stream(path) as stream:
        while block := stream.read(128 * 1024):
            total += len(block)
            if total > limit:
                raise RecoveryError("Expanded transcript exceeds byte limit; excluded.")
            yield block


def lines(path: Path, limit: int = MAX_BYTES):
    total = 0
    with source_stream(path) as stream:
        while line := stream.readline(MAX_LINE + 1):
            total += len(line)
            if len(line) > MAX_LINE or total > limit:
                raise RecoveryError("Transcript exceeds byte or line limit; excluded.")
            yield line


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with source_stream(path) as stream:
        while block := stream.read(128 * 1024):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, data: bytes):
    path_without_symlinks(path)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def read_small(path: Path, limit: int) -> bytes:
    """Bound metadata reads even if a file grows after its initial stat."""
    with source_stream(path) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise RecoveryError("Metadata input exceeds supported size limit.")
    return data


def publish_directory(stage: Path, destination: Path):
    """Reserve destination exclusively before replacing our own empty directory."""
    path_without_symlinks(destination)
    destination.mkdir(mode=0o700)  # Atomic failure when any destination already exists.
    reserved = destination.stat(follow_symlinks=False)
    try:
        os.replace(stage, destination)
    except BaseException:
        current = destination.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino) == (reserved.st_dev, reserved.st_ino):
            destination.rmdir()  # Only our empty reservation; never recursive deletion.
        raise


def token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:20]
