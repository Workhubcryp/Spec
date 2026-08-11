"""Directory browsing service."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import AppConfig
from ..filesystem.adapter import FilesystemAdapter
from ..filesystem.models import FileEntry
from ..security.path_resolver import PathResolver, ResolvedPath


@dataclass(frozen=True)
class DirectoryListing:
    current_path: str
    parent_path: str | None
    entries: list[FileEntry]


class DirectoryService:
    def __init__(self, filesystem: FilesystemAdapter, config: AppConfig):
        self.filesystem = filesystem
        self.resolver: PathResolver = filesystem.resolver
        self.config = config

    def browse(self, virtual_path: str = "", sort: str = "name", order: str = "asc") -> DirectoryListing:
        directory = self.resolver.resolve_directory(virtual_path)
        entries = self.filesystem.list_directory(
            directory,
            include_hidden=self.config.SHOW_HIDDEN_FILES,
        )
        entries.sort(key=lambda entry: self._sort_key(entry, sort), reverse=order == "desc")
        parent_path = self._parent_path(directory)
        return DirectoryListing(directory.relative_path, parent_path, entries)

    def _sort_key(self, entry: FileEntry, sort: str):
        if sort == "size":
            return (entry.size_bytes is None, entry.size_bytes or 0, entry.name.lower())
        if sort == "modified":
            return (entry.modified_at is None, entry.modified_at, entry.name.lower())
        if sort == "type":
            return (entry.kind, entry.name.lower())
        return (not entry.is_directory, entry.name.lower())

    def _parent_path(self, directory: ResolvedPath) -> str | None:
        if not directory.relative_path:
            return None
        parent = directory.path.parent.relative_to(self.resolver.base_dir)
        return parent.as_posix()
