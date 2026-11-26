"""Abertura explícita de diretórios e páginas pelo sistema operacional."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


class DesktopSystemOpener:
    def open_directory(self, path: Path) -> bool:
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_url(self, url: str) -> bool:
        return QDesktopServices.openUrl(QUrl(url))
