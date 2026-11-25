"""Localização de dados do aplicativo no perfil do usuário."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths


class AppPathsError(OSError):
    """Indica que a raiz local do aplicativo não pode ser preparada."""

    code = "APP_PATHS_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Diretórios locais gerenciados pelo aplicativo."""

    root: Path

    @classmethod
    def from_qstandardpaths(cls) -> AppPaths:
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        if not location:
            raise AppPathsError("O Windows não informou uma pasta local gravável.")
        return cls(Path(location))

    @classmethod
    def from_root(cls, root: Path) -> AppPaths:
        """Constrói paths com raiz injetada, usado em testes e composição."""
        return cls(root.expanduser().resolve())

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def settings_file(self) -> Path:
        return self.config / "settings.json"

    @property
    def database_file(self) -> Path:
        return self.data / "manga_to_kindle.sqlite3"

    @property
    def log_file(self) -> Path:
        return self.logs / "application.log"

    def ensure(self) -> None:
        try:
            for directory in (self.root, self.config, self.data, self.logs, self.cache):
                directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise AppPathsError(
                "Não foi possível criar os diretórios locais do aplicativo."
            ) from exc
