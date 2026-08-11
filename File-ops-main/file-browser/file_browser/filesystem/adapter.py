"""Filesystem operations that accept only already-resolved paths."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from ..security.exceptions import EntryNotFoundError
from ..security.path_resolver import PathResolver, ResolvedPath
from .models import FileEntry


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".xml",
    ".csv",
    ".ini",
    ".toml",
    ".sh",
}


class FilesystemAdapter:
    def __init__(self, resolver: PathResolver):
        self.resolver = resolver

    def list_directory(
        self,
        directory: ResolvedPath,
        include_hidden: bool = False,
    ) -> list[FileEntry]:
        entries: list[FileEntry] = []
        for child in directory.path.iterdir():
            if child.name.startswith(".") and not include_hidden:
                continue
            try:
                resolved_child = child.resolve(strict=True)
                resolved_child.relative_to(self.resolver.base_dir)
            except (OSError, ValueError):
                # Do not leak or follow links that leave BASE_DIR.
                continue

            is_symlink = child.is_symlink()
            if resolved_child.is_dir():
                kind = "directory"
                size_bytes = None
            elif resolved_child.is_file():
                kind = "file"
                size_bytes = resolved_child.stat().st_size
            else:
                continue
            stat = resolved_child.stat()
            relative_path = resolved_child.relative_to(self.resolver.base_dir).as_posix()
            mime_type = mimetypes.guess_type(child.name)[0]
            entries.append(
                FileEntry(
                    name=child.name,
                    relative_path=relative_path,
                    kind=kind,
                    size_bytes=size_bytes,
                    modified_at=datetime_from_timestamp(stat.st_mtime),
                    mime_type=mime_type,
                    previewable=kind == "file" and self.is_previewable(child),
                    downloadable=kind == "file",
                    is_symlink=is_symlink,
                )
            )
        return entries

    def stat(self, resolved: ResolvedPath) -> Path:
        if not resolved.path.exists():
            raise EntryNotFoundError(resolved.relative_path)
        return resolved.path

    def is_previewable(self, path: Path) -> bool:
        mime_type = mimetypes.guess_type(path.name)[0] or ""
        return (
            path.suffix.lower() in TEXT_EXTENSIONS
            or mime_type.startswith("image/")
            or mime_type == "application/pdf"
        )

    def mime_type(self, path: Path) -> str:
        return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def datetime_from_timestamp(timestamp: float):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, tz=timezone.utc)