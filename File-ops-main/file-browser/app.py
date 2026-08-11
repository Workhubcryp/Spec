"""Convenience entry point for the File Browser application."""

from file_browser.app import create_app
from file_browser.config import load_config

app = create_app()


if __name__ == "__main__":
    config = load_config()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)