"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"Expected an integer configuration value, got {value!r}") from error
    if parsed <= 0:
        raise ValueError(f"Expected a positive configuration value, got {parsed}")
    return parsed


@dataclass(frozen=True)
class AppConfig:
    BASE_DIR: Path
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    SHOW_HIDDEN_FILES: bool = False
    MAX_PREVIEW_BYTES: int = 2 * 1024 * 1024
    LOG_LEVEL: str = "INFO"

    def as_flask_config(self) -> dict[str, object]:
        return {
            "BASE_DIR": self.BASE_DIR,
            "HOST": self.HOST,
            "PORT": self.PORT,
            "DEBUG": self.DEBUG,
            "SHOW_HIDDEN_FILES": self.SHOW_HIDDEN_FILES,
            "MAX_PREVIEW_BYTES": self.MAX_PREVIEW_BYTES,
            "LOG_LEVEL": self.LOG_LEVEL,
            "MAX_CONTENT_LENGTH": self.MAX_PREVIEW_BYTES,
        }


def load_config(
    overrides: Mapping[str, object] | None = None,
) -> AppConfig:
    """Load configuration, validating BASE_DIR before the server starts."""

    base_dir_value = os.environ.get("FILE_BROWSER_BASE_DIR", ".")
    base_dir = Path(base_dir_value).expanduser().resolve()
    if not base_dir.exists():
        raise ValueError(f"FILE_BROWSER_BASE_DIR does not exist: {base_dir}")
    if not base_dir.is_dir():
        raise ValueError(f"FILE_BROWSER_BASE_DIR is not a directory: {base_dir}")

    values: dict[str, object] = {
        "BASE_DIR": base_dir,
        "HOST": os.environ.get("FILE_BROWSER_HOST", "0.0.0.0"),
        "PORT": _env_int(os.environ.get("FILE_BROWSER_PORT"), 8000),
        "DEBUG": _env_bool(os.environ.get("FILE_BROWSER_DEBUG"), False),
        "SHOW_HIDDEN_FILES": _env_bool(
            os.environ.get("FILE_BROWSER_SHOW_HIDDEN_FILES"), False
        ),
        "MAX_PREVIEW_BYTES": _env_int(
            os.environ.get("FILE_BROWSER_MAX_PREVIEW_BYTES"),
            2 * 1024 * 1024,
        ),
        "LOG_LEVEL": os.environ.get("FILE_BROWSER_LOG_LEVEL", "INFO").upper(),
    }
    if overrides:
        values.update(overrides)
    values["BASE_DIR"] = Path(values["BASE_DIR"]).expanduser().resolve()
    if not values["BASE_DIR"].is_dir():
        raise ValueError(f"BASE_DIR is not a directory: {values['BASE_DIR']}")
    return AppConfig(**values)