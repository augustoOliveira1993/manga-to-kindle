"""Contrato imutável de página com referência preservada à imagem original."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

from manga_to_kindle.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class Page:
    chapter_id: UUID
    position: int
    original_path: Path
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.position < 0:
            raise DomainValidationError("A posição da página não pode ser negativa.")
        if not str(self.original_path).strip() or self.original_path == Path("."):
            raise DomainValidationError("A página precisa referenciar uma imagem original local.")
