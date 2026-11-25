"""Encerramento ordenado e seguro dos recursos locais."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from logging import Logger

from manga_to_kindle.infrastructure.config.settings import AppSettings
from manga_to_kindle.infrastructure.logging import LoggingManager
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase


@dataclass(slots=True)
class ApplicationRuntime:
    """Recursos injetados da sessão atual do aplicativo."""

    paths: AppPaths
    settings: AppSettings
    logging: LoggingManager
    database: SQLiteDatabase
    _shutdown_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    @property
    def logger(self) -> Logger:
        return self.logging.logger

    @property
    def closed(self) -> bool:
        return self._closed

    def shutdown(self) -> None:
        """Fecha a base antes do logger; pode ser chamado por um worker Qt."""
        with self._shutdown_lock:
            if self._closed:
                return
            try:
                self.database.close()
            except Exception as exc:
                self.logger.error(
                    "shutdown failed code=%s exception_type=%s",
                    getattr(exc, "code", "DATABASE_SHUTDOWN_FAILED"),
                    type(exc).__name__,
                )
                raise
            self.logger.info("application shutdown complete")
            self.logging.close()
            self._closed = True
