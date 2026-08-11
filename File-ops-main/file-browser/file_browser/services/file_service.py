"""Download and file metadata service."""

from __future__ import annotations

from ..filesystem.adapter import FilesystemAdapter
from ..security.path_resolver import PathResolver


class FileService:
    def __init__(self, filesystem: FilesystemAdapter):
        self.filesystem = filesystem
        self.resolver: PathResolver = filesystem.resolver

    def get_download_path(self, virtual_path: str):
        return self.resolver.resolve_file(virtual_path).path

    def get_mime_type(self, virtual_path: str) -> str:
        path = self.resolver.resolve_file(virtual_path).path
        return self.filesystem.mime_type(path)