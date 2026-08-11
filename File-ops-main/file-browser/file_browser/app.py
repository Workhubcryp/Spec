"""Flask application factory and shared error handling."""

from __future__ import annotations

import logging
from dataclasses import fields
from pathlib import Path

from flask import Flask, render_template

from .config import AppConfig, load_config
from .filesystem.adapter import FilesystemAdapter
from .routes.files import files_bp
from .routes.preview import preview_bp
from .security.exceptions import (
    EntryNotFoundError,
    FileBrowserError,
    NotDirectoryError,
    NotFileError,
    PathSecurityError,
    PreviewTooLargeError,
)
from .security.path_resolver import PathResolver
from .services.directory_service import DirectoryService
from .services.file_service import FileService
from .services.preview_service import PreviewService


def create_app(config_overrides: dict[str, object] | None = None) -> Flask:
    """Create a configured Flask application.

    The application keeps the filesystem boundary in ``PathResolver`` and
    exposes services to route modules through ``app.extensions``.
    """

    config_fields = {field.name for field in fields(AppConfig)}
    application_overrides = {
        key: value
        for key, value in (config_overrides or {}).items()
        if key in config_fields
    }
    flask_overrides = {
        key: value
        for key, value in (config_overrides or {}).items()
        if key not in config_fields
    }
    config = load_config(application_overrides)
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parents[1] / "templates"),
        static_folder=str(Path(__file__).parents[1] / "static"),
    )
    app.config.update(config.as_flask_config())
    app.config.update(flask_overrides)

    resolver = PathResolver(config.BASE_DIR)
    filesystem = FilesystemAdapter(resolver)
    app.extensions["file_browser.services"] = {
        "directory": DirectoryService(filesystem, config),
        "file": FileService(filesystem),
        "preview": PreviewService(filesystem, config),
    }

    app.register_blueprint(files_bp)
    app.register_blueprint(preview_bp)
    _register_error_handlers(app)
    _configure_logging(app)
    return app


def _configure_logging(app: Flask) -> None:
    if not app.logger.handlers:
        logging.basicConfig(
            level=getattr(logging, app.config["LOG_LEVEL"], logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    app.logger.setLevel(app.config["LOG_LEVEL"])


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(EntryNotFoundError)
    @app.errorhandler(NotDirectoryError)
    @app.errorhandler(NotFileError)
    def handle_not_found(error: FileBrowserError):
        return render_template(
            "error.html",
            status_code=404,
            title="Not Found",
            message=error.user_message,
        ), 404

    @app.errorhandler(PathSecurityError)
    def handle_forbidden(error: PathSecurityError):
        return render_template(
            "error.html",
            status_code=403,
            title="Forbidden",
            message=error.user_message,
        ), 403

    @app.errorhandler(PreviewTooLargeError)
    def handle_preview_too_large(error: PreviewTooLargeError):
        return render_template(
            "error.html",
            status_code=413,
            title="Preview Too Large",
            message=error.user_message,
        ), 413

    @app.errorhandler(404)
    def handle_http_not_found(_error):
        return render_template(
            "error.html",
            status_code=404,
            title="Not Found",
            message="指定されたページは見つかりません。",
        ), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        app.logger.exception("Unhandled application error", exc_info=error)
        return render_template(
            "error.html",
            status_code=500,
            title="Internal Server Error",
            message="処理中に予期しないエラーが発生しました。",
        ), 500