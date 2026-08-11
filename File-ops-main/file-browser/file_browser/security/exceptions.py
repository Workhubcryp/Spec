"""Domain exceptions that become safe HTTP responses."""


class FileBrowserError(Exception):
    """Base exception with a message safe to show to an end user."""

    user_message = "ファイル操作に失敗しました。"


class PathSecurityError(FileBrowserError):
    user_message = "指定された場所にはアクセスできません。"


class EntryNotFoundError(FileBrowserError):
    user_message = "ファイルまたはフォルダが見つかりません。"


class NotDirectoryError(FileBrowserError):
    user_message = "指定された場所はフォルダではありません。"


class NotFileError(FileBrowserError):
    user_message = "指定された場所はファイルではありません。"


class PreviewTooLargeError(FileBrowserError):
    user_message = "このファイルはプレビューできるサイズを超えています。"