"""Inline preview routes."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, send_file

from ..services.preview_service import PreviewService

preview_bp = Blueprint("preview", __name__)


def _preview_service() -> PreviewService:
    return current_app.extensions["file_browser.services"]["preview"]


@preview_bp.get("/preview/<path:virtual_path>")
def preview(virtual_path: str):
    service = _preview_service()
    path = service.resolver.resolve_file(virtual_path).path
    mime_type = service.filesystem.mime_type(path)
    if mime_type.startswith("image/") or mime_type == "application/pdf":
        return send_file(path, mimetype=mime_type, as_attachment=False, conditional=True)
    text_preview = service.get_text_preview(virtual_path)
    return render_template("preview.html", preview=text_preview)