"""Resolve virtual browser paths without allowing filesystem escape."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote

from .exceptions import (
    EntryNotFoundError,
    NotDirectoryError,
    NotFileError,
    PathSecurityError,
)


@dataclass(frozen=True)
class ResolvedPath:
    path: Path
    relative_path: str


class PathResolver:
    """The only component allowed to turn a user path into a filesystem path."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve(strict=True)
        if not self.base_dir.is_dir():
            raise NotDirectoryError(str(self.base_dir))

    def resolve(self, virtual_path: str | None = "") -> ResolvedPath:
        raw = unquote(virtual_path or "")
        if "\x00" in raw or "\\" in raw:
            raise PathSecurityError(raw)
        if raw.startswith("/") or PureWindowsPath(raw).drive:
            raise PathSecurityError(raw)

        parts: list[str] = []
        for component in raw.split("/"):
            if component in {"", "."}:
                continue
            if component == "..":
                raise PathSecurityError(raw)
            parts.append(component)

        candidate = self.base_dir.joinpath(*parts)
        try:
            resolved = candidate.resolve(strict=False)
            relative = resolved.relative_to(self.base_dir)
        except (OSError, ValueError) as error:
            raise PathSecurityError(raw) from error

        if not self._is_within_base(resolved):
            raise PathSecurityError(raw)
        if not resolved.exists():
            raise EntryNotFoundError(raw)
        relative_path = "" if relative == Path(".") else relative.as_posix()
        return ResolvedPath(resolved, relative_path)

    def resolve_directory(self, virtual_path: str | None = "") -> ResolvedPath:
        resolved = self.resolve(virtual_path)
        if not resolved.path.is_dir():
            raise NotDirectoryError(virtual_path or "")
        return resolved

    def resolve_file(self, virtual_path: str) -> ResolvedPath:
        resolved = self.resolve(virtual_path)
        if not resolved.path.is_file():
            raise NotFileError(virtual_path)
        return resolved

    def resolve_child(self, parent: ResolvedPath, child_name: str) -> ResolvedPath:
        if not child_name or child_name in {".", ".."}:
            raise PathSecurityError(child_name)
        return self.resolve(f"{parent.relative_path}/{child_name}")

    def _is_within_base(self, path: Path) -> bool:
        try:
            path.relative_to(self.base_dir)
        except ValueError:
            return False
        return True