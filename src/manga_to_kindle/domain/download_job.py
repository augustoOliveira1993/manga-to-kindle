"""Contrato de job persistente sem iniciar qualquer operação de rede."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from manga_to_kindle.domain.errors import DomainValidationError

_KEEP_TOTAL = object()


class DownloadState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATES = {DownloadState.SUCCEEDED, DownloadState.FAILED, DownloadState.CANCELLED}
_ALLOWED_TRANSITIONS = {
    DownloadState.QUEUED: {DownloadState.RUNNING, DownloadState.FAILED, DownloadState.CANCELLED},
    DownloadState.RUNNING: {
        DownloadState.PAUSED,
        DownloadState.SUCCEEDED,
        DownloadState.FAILED,
        DownloadState.CANCELLED,
    },
    DownloadState.PAUSED: {DownloadState.RUNNING, DownloadState.CANCELLED},
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class DownloadJob:
    id: UUID = field(default_factory=uuid4)
    target_manga_id: UUID | None = None
    target_chapter_id: UUID | None = None
    state: DownloadState = DownloadState.QUEUED
    progress: int = 0
    total: int | None = None
    cancel_requested: bool = False
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        targets = sum(
            target is not None for target in (self.target_manga_id, self.target_chapter_id)
        )
        if targets != 1:
            raise DomainValidationError("Um DownloadJob precisa de exatamente um alvo.")
        if self.progress < 0:
            raise DomainValidationError("O progresso do download não pode ser negativo.")
        if self.total is not None and (self.total < 0 or self.progress > self.total):
            raise DomainValidationError("O progresso não pode exceder o total conhecido.")
        if self.created_at.utcoffset() is None or self.updated_at.utcoffset() is None:
            raise DomainValidationError("Os horários do job precisam conter fuso UTC.")

    def transition_to(self, next_state: DownloadState) -> DownloadJob:
        if self.state in _TERMINAL_STATES:
            raise DomainValidationError("Um estado terminal do download não pode ser reaberto.")
        if next_state not in _ALLOWED_TRANSITIONS.get(self.state, set()):
            raise DomainValidationError("A transição de estado do download não é permitida.")
        return replace(self, state=next_state, updated_at=_utc_now())

    def with_progress(
        self,
        progress: int,
        total: int | None | object = _KEEP_TOTAL,
    ) -> DownloadJob:
        if self.state is not DownloadState.RUNNING:
            raise DomainValidationError("O progresso só pode mudar durante a execução.")
        new_total = self.total if total is _KEEP_TOTAL else total
        return replace(
            self,
            progress=progress,
            total=new_total,  # type: ignore[arg-type]
            updated_at=_utc_now(),
        )

    def request_cancellation(self) -> DownloadJob:
        if self.state in _TERMINAL_STATES:
            raise DomainValidationError("Um job terminal não aceita novo pedido de cancelamento.")
        return replace(self, cancel_requested=True, updated_at=_utc_now())
