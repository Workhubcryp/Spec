"""Preview policy and bounded text reads."""

from __future__ import annotations

import html
from dataclasses import dataclass

import markdown as markdown_lib

from ..config import AppConfig
from ..filesystem.adapter import FilesystemAdapter
from ..security.exceptions import NotFileError, PreviewTooLargeError
from ..security.path_resolver import PathResolver

MARKDOWN_EXTENSIONS = ["extra", "sane_lists", "fenced_code", "tables", "toc"]


@dataclass(frozen=True)
class TextPreview:
    name: str
    relative_path: str
    content: str
    is_markdown: bool
    rendered_html: str | None = None


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
        text = content.decode("utf-8", errors="replace")
        is_markdown = resolved.path.suffix.lower() == ".md"
        return TextPreview(
            name=resolved.path.name,
            relative_path=resolved.relative_path,
            content=text,
            is_markdown=is_markdown,
            rendered_html=self._render_markdown(text) if is_markdown else None,
        )

    @staticmethod
    def _render_markdown(text: str) -> str:
        # Escape literal HTML in the source before conversion, so any
        # embedded tags/scripts in a .md file are displayed as plain text
        # rather than executed in the browser. Markdown syntax itself does
        # not rely on angle brackets, so normal formatting is unaffected.
        escaped = html.escape(text, quote=False)
        return markdown_lib.markdown(escaped, extensions=MARKDOWN_EXTENSIONS)