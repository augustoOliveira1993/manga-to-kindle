"""Controles cooperativos persistidos para cada trabalho da fila."""

from __future__ import annotations

import threading
from uuid import UUID

from manga_to_kindle.application.downloads.errors import DownloadRecordNotFound
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.infrastructure.persistence.download_repository import DownloadRepository


class DownloadControlSignals:
    """Sinais em memória compartilhados pelo coordenador e pelos controles."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancel: dict[UUID, threading.Event] = {}
        self._pause: dict[UUID, threading.Event] = {}

    def cancel_event(self, job_id: UUID) -> threading.Event:
        with self._lock:
            return self._cancel.setdefault(job_id, threading.Event())

    def pause_event(self, job_id: UUID) -> threading.Event:
        with self._lock:
            return self._pause.setdefault(job_id, threading.Event())

    def cancel(self, job_id: UUID) -> None:
        self.cancel_event(job_id).set()

    def pause(self, job_id: UUID) -> None:
        self.pause_event(job_id).set()

    def resume(self, job_id: UUID) -> None:
        self.pause_event(job_id).clear()


class DownloadControls:
    def __init__(
        self,
        repository: DownloadRepository,
        signals: DownloadControlSignals,
    ) -> None:
        self._repository = repository
        self._signals = signals

    def pause(self, job_id: UUID) -> None:
        snapshot = self._repository.get(job_id)
        if snapshot is None:
            raise DownloadRecordNotFound("O trabalho não foi encontrado.")
        if snapshot.job.state is not DownloadState.RUNNING:
            raise DomainValidationError("Somente um trabalho em execução pode ser pausado.")
        self._repository.set_job_state(job_id, DownloadState.PAUSED)
        self._signals.pause(job_id)

    def resume(self, job_id: UUID) -> None:
        snapshot = self._repository.get(job_id)
        if snapshot is None:
            raise DownloadRecordNotFound("O trabalho não foi encontrado.")
        if snapshot.job.state not in {DownloadState.PAUSED, DownloadState.INTERRUPTED}:
            raise DomainValidationError(
                "Somente um trabalho pausado ou interrompido pode ser retomado."
            )
        self._signals.resume(job_id)
        self._repository.set_job_state(job_id, DownloadState.RUNNING)

    def cancel(self, job_id: UUID) -> None:
        snapshot = self._repository.get(job_id)
        if snapshot is None:
            raise DownloadRecordNotFound("O trabalho não foi encontrado.")
        if snapshot.job.state is DownloadState.RUNNING:
            self._repository.request_cancel(job_id)
            self._signals.cancel(job_id)
            return
        self._repository.set_job_state(job_id, DownloadState.CANCELLED)
        self._signals.cancel(job_id)
