"""Persistent content-addressed files, verified on admission and after modification."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
from collections.abc import Iterable
from pathlib import Path


def fingerprint(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_dev, stat.st_ino


class ContentCache:
    """A mounted release remains authoritative; cached files are expendable.

    The full SHA-256 is the identity. A receipt permits unchanged local files to
    survive process restarts without rereading their bytes. Changed files are
    rehashed, never accepted by size alone. Publication uses atomic replacement.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self._verified: dict[Path, tuple[int, int, int, int, int]] = {}
        self._lock = threading.RLock()

    def _path(self, sha256: str, suffix: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError("Invalid content hash")
        if not re.fullmatch(r"\.[a-zA-Z0-9]{1,12}", suffix):
            raise ValueError("Invalid cached file extension")
        path = self.root / sha256[:2] / (sha256 + suffix)
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError("Cache path escapes its root")
        return path

    def _remember(self, path: Path) -> None:
        stamp = fingerprint(path)
        receipt = path.with_name(path.name + ".verified.json")
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False,
                                         prefix=".receipt-", encoding="utf-8") as output:
            temporary = Path(output.name)
            json.dump(stamp, output)
        try:
            os.replace(temporary, receipt)
            self._verified[path] = stamp
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, sha256: str, size: int, suffix: str) -> Path | None:
        """Return a verified local file, or None when missing/corrupt."""
        with self._lock:
            path = self._path(sha256, suffix)
            try:
                stamp = fingerprint(path)
                if stamp[0] != size:
                    return None
                if self._verified.get(path) == stamp:
                    return path
                receipt = path.with_name(path.name + ".verified.json")
                if not receipt.is_symlink() and tuple(json.loads(receipt.read_text())) == stamp:
                    self._verified[path] = stamp
                    return path
            except (OSError, ValueError, TypeError):
                pass
            try:
                before = fingerprint(path)
                hasher = hashlib.sha256()
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        hasher.update(chunk)
                if before != fingerprint(path) or before[0] != size or hasher.hexdigest() != sha256:
                    return None
                self._remember(path)
                return path
            except OSError:
                return None

    def put(self, sha256: str, size: int, suffix: str, chunks: Iterable[bytes]) -> Path:
        """Consume and verify chunks before publishing; failures leave no partial file."""
        with self._lock:
            path = self._path(sha256, suffix)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, prefix=".asset-") as output:
                    temporary = Path(output.name)
                    hasher = hashlib.sha256()
                    received = 0
                    for chunk in chunks:
                        received += len(chunk)
                        if received > size:
                            raise ValueError("Cached content byte budget exceeded")
                        output.write(chunk)
                        hasher.update(chunk)
                if received != size or hasher.hexdigest() != sha256:
                    raise ValueError("Cached content hash mismatch")
                os.replace(temporary, path)
                self._remember(path)
                return path
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)

    def import_file(self, sha256: str, size: int, source: Path) -> Path:
        existing = self.get(sha256, size, source.suffix)
        if existing is not None:
            return existing
        with source.open("rb") as stream:
            return self.put(sha256, size, source.suffix,
                            iter(lambda: stream.read(1024 * 1024), b""))
