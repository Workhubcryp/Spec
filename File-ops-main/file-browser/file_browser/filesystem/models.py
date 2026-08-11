"""Filesystem DTOs used by services and templates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


EntryKind = Literal["directory", "file", "symlink"]


@dataclass(frozen=True)
class FileEntry:
    name: str
    relative_path: str
    kind: EntryKind
    size_bytes: int | None
    modified_at: datetime | None
    mime_type: str | None
    previewable: bool
    downloadable: bool
    is_symlink: bool = False

    @property
    def is_directory(self) -> bool:
        return self.kind == "directory"