"""Configuração local validada e gravada de forma atômica."""

from __future__ import annotations

import os
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from manga_to_kindle.application.ui.theme_mode import ThemeMode
from manga_to_kindle.infrastructure.paths import AppPaths


class AppSettings(BaseModel):
    """Preferências locais da fundação, sem credenciais nem conteúdo de livros."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    log_max_bytes: int = Field(default=5 * 1024 * 1024, ge=64 * 1024, le=100 * 1024 * 1024)
    log_backup_count: int = Field(default=3, ge=1, le=10)
    theme: ThemeMode = "light"


class InvalidSettingsError(ValueError):
    """Configuração ausente ou inválida; o arquivo original é preservado."""

    code = "INVALID_LOCAL_CONFIGURATION"

    def __init__(self, fields: tuple[str, ...] = ()) -> None:
        self.fields = fields
        super().__init__("A configuração local é inválida e foi preservada para diagnóstico.")


class SettingsWriteError(OSError):
    """Falha ao persistir a configuração local."""

    code = "LOCAL_CONFIGURATION_WRITE_FAILED"


def load_or_create_settings(paths: AppPaths) -> AppSettings:
    """Carrega a configuração, criando defaults somente quando ela não existe."""
    try:
        content = paths.settings_file.read_bytes()
    except FileNotFoundError:
        settings = AppSettings()
        save_settings(paths, settings)
        return settings
    except OSError as exc:
        raise InvalidSettingsError() from exc

    try:
        return AppSettings.model_validate_json(content)
    except ValidationError as exc:
        fields = tuple(
            sorted({".".join(str(part) for part in error["loc"]) for error in exc.errors()})
        )
        raise InvalidSettingsError(fields) from None


def save_settings(paths: AppPaths, settings: AppSettings) -> None:
    """Grava JSON com flush/fsync e substituição atômica no mesmo diretório."""
    temporary_path = paths.settings_file.with_name(
        f".{paths.settings_file.name}.{uuid4().hex}.tmp"
    )
    try:
        with temporary_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(settings.model_dump_json(indent=2))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, paths.settings_file)
    except OSError as exc:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise SettingsWriteError("Não foi possível salvar a configuração local.") from exc
