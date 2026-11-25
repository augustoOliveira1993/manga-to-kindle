"""Contrato de pedido de exportação local."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.errors import DomainValidationError


class ExportState(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATES = {ExportState.COMPLETED, ExportState.FAILED, ExportState.CANCELLED}
_ALLOWED_TRANSITIONS = {
    ExportState.REQUESTED: {ExportState.RUNNING, ExportState.FAILED, ExportState.CANCELLED},
    ExportState.RUNNING: {ExportState.COMPLETED, ExportState.FAILED, ExportState.CANCELLED},
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Export:
    chapter_ids: tuple[UUID, ...]
    device_profile: DeviceProfile
    destination: Path
    id: UUID = field(default_factory=uuid4)
    state: ExportState = ExportState.REQUESTED
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.chapter_ids:
            raise DomainValidationError("A exportação precisa referenciar pelo menos um capítulo.")
        if len(self.chapter_ids) != len(set(self.chapter_ids)):
            raise DomainValidationError("A exportação não pode repetir capítulos.")
        if not self.destination.is_absolute():
            raise DomainValidationError(
                "O destino da exportação precisa ser um caminho local absoluto."
            )
        if self.created_at.utcoffset() is None:
            raise DomainValidationError("O horário da exportação precisa conter fuso UTC.")

    def transition_to(self, next_state: ExportState) -> Export:
        if self.state in _TERMINAL_STATES:
            raise DomainValidationError("Um estado terminal da exportação não pode ser reaberto.")
        if next_state not in _ALLOWED_TRANSITIONS.get(self.state, set()):
            raise DomainValidationError("A transição de estado da exportação não é permitida.")
        return replace(self, state=next_state)
