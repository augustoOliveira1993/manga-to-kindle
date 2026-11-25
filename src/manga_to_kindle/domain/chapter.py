"""Contrato imutável de capítulo."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from manga_to_kindle.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class Chapter:
    manga_id: UUID
    position: int
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    number: Decimal | None = None
    volume: Decimal | None = None
    available: bool | None = None
    source_order: int | None = None

    def __post_init__(self) -> None:
        if self.position < 0:
            raise DomainValidationError("A posição do capítulo não pode ser negativa.")
        if self.title is not None and not self.title.strip():
            raise DomainValidationError("O título do capítulo não pode ser vazio.")
        if self.number is not None and not self.number.is_finite():
            raise DomainValidationError("O número do capítulo precisa ser finito.")
        if self.volume is not None and not self.volume.is_finite():
            raise DomainValidationError("O volume do capítulo precisa ser finito.")
        if self.source_order is not None and self.source_order < 0:
            raise DomainValidationError("A ordem declarada pela fonte não pode ser negativa.")
        if self.available is not None and not isinstance(self.available, bool):
            raise DomainValidationError("A disponibilidade precisa ser booleana ou ausente.")
        if self.title is None and self.number is None:
            raise DomainValidationError("O capítulo precisa de título ou número de exibição.")
