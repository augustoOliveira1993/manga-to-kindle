"""Logging rotativo local com remoção de dados sensíveis antes da gravação."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from manga_to_kindle.infrastructure.config.settings import AppSettings

_URL_PATTERN = re.compile(r"(?i)\bhttps?://[^\s\]\[<>\"']+")
_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|passwd|token|secret|authorization|api[_-]?key|credential)"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|bearer\s+[^\s,;]+|[^\s,;]+)"
)
_BOOK_CONTENT_PATTERN = re.compile(
    r"(?i)\b(book(?:_title|_content)?|manga(?:_title)?|chapter_content|page_content|content)"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\r\n,;]+)"
)
_WINDOWS_PATH_PATTERN = re.compile(r"(?i)\b[a-z]:\\[^\s,;]+")


def redact_log_message(message: str) -> str:
    """Redige URLs, credenciais, conteúdo identificado e caminhos absolutos."""
    redacted = _URL_PATTERN.sub("[URL REDACTED]", message)
    redacted = _SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    redacted = _BOOK_CONTENT_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    return _WINDOWS_PATH_PATTERN.sub("[PATH REDACTED]", redacted)


class SensitiveDataFilter(logging.Filter):
    """Sanitiza a mensagem e remove valores de exceções antes do formatter."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact_log_message(record.getMessage())
        except Exception:
            record.msg = "[mensagem de log inválida; conteúdo omitido]"
        record.args = ()
        if record.exc_info is not None:
            exception_type = record.exc_info[0]
            name = exception_type.__name__ if exception_type is not None else "Exception"
            record.exc_info = None
            record.exc_text = f"[tipo de exceção: {name}; detalhes omitidos]"
        if record.stack_info is not None:
            record.stack_info = "[stack omitida]"
        return True


class LoggingSetupError(OSError):
    """Não foi possível preparar o arquivo de log local."""

    code = "LOGGING_SETUP_FAILED"


class LoggingManager:
    """Dono dos handlers da aplicação e responsável por fechá-los no shutdown."""

    def __init__(self, logger: logging.Logger, handler: RotatingFileHandler) -> None:
        self.logger = logger
        self._handler = handler
        self._closed = False
        self._settings: AppSettings | None = None

    def configure(self, log_file: Path, settings: AppSettings) -> None:
        if self._closed:
            raise LoggingSetupError("O logging já foi encerrado.")
        handler = _create_handler(log_file, settings)
        self.logger.removeHandler(self._handler)
        self._handler.close()
        self._handler = handler
        self.logger.addHandler(handler)
        self._settings = settings

    def close(self) -> None:
        if self._closed:
            return
        self.logger.removeHandler(self._handler)
        self._handler.flush()
        self._handler.close()
        self._closed = True


def _create_handler(log_file: Path, settings: AppSettings) -> RotatingFileHandler:
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_file,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
            delay=False,
        )
    except OSError as exc:
        raise LoggingSetupError("Não foi possível abrir o arquivo de log local.") from exc
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    return handler


def configure_logging(
    log_file: Path,
    settings: AppSettings,
    logger_name: str = "manga_to_kindle",
) -> LoggingManager:
    """Inicializa o logger sem propagar conteúdo para handlers globais."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for existing_handler in tuple(logger.handlers):
        logger.removeHandler(existing_handler)
        existing_handler.close()

    handler = _create_handler(log_file, settings)
    logger.addHandler(handler)
    manager = LoggingManager(logger, handler)
    manager._settings = settings
    return manager
