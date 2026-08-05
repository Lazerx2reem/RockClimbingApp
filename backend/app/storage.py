"""Pluggable object storage for uploaded videos.

Dev uses a local-disk backend under ``settings.media_root``. The interface is
deliberately S3-shaped (``save``/``open``/``delete``/``local_path``) so a
future ``S3Storage`` can drop in without touching the routers or the analyzer.

The analyzer needs a real filesystem path (OpenCV reads by path), so callers
use the ``local_path`` context manager: the local backend yields the file in
place; a remote backend would download to a temp file and clean it up on exit.
"""
from __future__ import annotations

import os
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, Protocol

from .config import settings


def new_storage_key(original_filename: str, prefix: str = "videos") -> str:
    """A collision-free storage key that preserves the original extension."""
    ext = Path(original_filename).suffix.lower()
    return f"{prefix}/{uuid.uuid4().hex}{ext}"


class Storage(Protocol):
    def save(self, key: str, fileobj: BinaryIO) -> int:
        """Persist a file object under ``key``; return the number of bytes written."""

    def open(self, key: str) -> BinaryIO: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...

    @contextmanager
    def local_path(self, key: str) -> Iterator[str]:
        """Yield a filesystem path to the object's bytes for the block's duration."""
        ...


class LocalStorage:
    """Stores objects as files under ``root``."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _full(self, key: str) -> Path:
        path = (self.root / key).resolve()
        # Guard against path traversal via a crafted key.
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    def save(self, key: str, fileobj: BinaryIO) -> int:
        dest = self._full(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as out:
            shutil.copyfileobj(fileobj, out)
        return dest.stat().st_size

    def open(self, key: str) -> BinaryIO:
        return open(self._full(key), "rb")

    def delete(self, key: str) -> None:
        self._full(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._full(key).exists()

    def path(self, key: str) -> str:
        """Stable on-disk path (local backend only) — used for range streaming."""
        return str(self._full(key))

    @contextmanager
    def local_path(self, key: str) -> Iterator[str]:
        yield str(self._full(key))


def _build_storage() -> Storage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.media_root)
    raise ValueError(f"Unsupported storage backend: {settings.storage_backend!r}")


# Single process-wide instance.
storage: Storage = _build_storage()
