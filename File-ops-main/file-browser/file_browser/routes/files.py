"""HTML browsing and download routes."""

from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, send_file, url_for

from ..services.directory_service import DirectoryService
from ..services.file_service import FileService

files_bp = Blueprint("files", __name__)


def _directory_service() -> DirectoryService:
    return current_app.extensions["file_browser.services"]["directory"]


def _file_service() -> FileService:
    return current_app.extensions["file_browser.services"]["file"]


@files_bp.get("/")
def root():
    return redirect(url_for("files.browse", virtual_path=""))


@files_bp.get("/browse/", defaults={"virtual_path": ""})
@files_bp.get("/browse/<path:virtual_path>")
def browse(virtual_path: str):
    listing = _directory_service().browse(
        virtual_path,
        sort=request.args.get("sort", "name"),
        order=request.args.get("order", "asc"),
    )
    return render_template(
        "index.html",
        listing=listing,
        sort=request.args.get("sort", "name"),
        order=request.args.get("order", "asc"),
    )


@files_bp.get("/download/<path:virtual_path>")
def download(virtual_path: str):
    path = _file_service().get_download_path(virtual_path)
    return send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        conditional=True,
    )