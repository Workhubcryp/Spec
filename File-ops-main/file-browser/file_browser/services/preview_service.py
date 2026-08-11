"""Preview policy and bounded text reads."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import AppConfig
from ..filesystem.adapter import FilesystemAdapter
from ..security.exceptions import NotFileError, PreviewTooLargeError
from ..security.path_resolver import PathResolver


@dataclass(frozen=True)
class TextPreview:
    name: str
    relative_path: str
    content: str


class PreviewService:
    def __init__(self, filesystem: FilesystemAdapter, config: AppConfig):
        self.filesystem = filesystem
        self.resolver: PathResolver = filesystem.resolver
        self.config = config

    def get_text_preview(self, virtual_path: str) -> TextPreview:
        resolved = self.resolver.resolve_file(virtual_path)
        if not self.filesystem.is_previewable(resolved.path):
            raise NotFileError(virtual_path)
        mime_type = self.filesystem.mime_type(resolved.path)
        if not (resolved.path.suffix.lower() in {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".html", ".htm", ".css", ".js", ".ts", ".tsx", ".jsx", ".xml", ".csv", ".ini", ".toml", ".sh"} or mime_type.startswith("text/")):
            raise NotFileError(virtual_path)
        content = resolved.path.read_bytes()
        if len(content) > self.config.MAX_PREVIEW_BYTES:
            raise PreviewTooLargeError(virtual_path)
        return TextPreview(
            name=resolved.path.name,
            relative_path=resolved.relative_path,
            content=content.decode("utf-8", errors="replace"),
        )