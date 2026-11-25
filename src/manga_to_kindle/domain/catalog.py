"""Snapshot completo de catálogo recebido de um provider selecionado."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.manga import Manga


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    provider_id: str
    source_id: str
    manga: Manga
    updated_at: datetime
    simulated: bool

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.source_id.strip():
            raise DomainValidationError("O catálogo precisa de identidades estáveis.")
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise DomainValidationError("A atualização do catálogo precisa de fuso horário.")

    @property
    def chapters(self) -> tuple[Chapter, ...]:
        return self.manga.chapters
