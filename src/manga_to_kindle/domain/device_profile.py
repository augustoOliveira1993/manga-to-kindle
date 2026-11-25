"""Perfil de saída validado sem pressupor capacidades físicas de um Kindle."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID, uuid4

from manga_to_kindle.domain.errors import DomainValidationError

type PreferenceValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    name: str
    id: UUID = field(default_factory=uuid4)
    preferences: Mapping[str, PreferenceValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("O perfil de dispositivo precisa de um nome.")
        copied = dict(self.preferences)
        for key, value in copied.items():
            if not key.strip():
                raise DomainValidationError("A preferência precisa de uma chave não vazia.")
            if isinstance(value, float) and not math.isfinite(value):
                raise DomainValidationError("Valores numéricos do perfil precisam ser finitos.")
            if not isinstance(value, str | int | float | bool | type(None)):
                raise DomainValidationError("O perfil contém um tipo de preferência inválido.")
        object.__setattr__(self, "preferences", MappingProxyType(copied))
