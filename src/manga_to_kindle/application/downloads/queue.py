"""Agendamento limitado, retry persistente e progresso por página."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from manga_to_kindle.application.downloads.controls import DownloadControlSignals
from manga_to_kindle.application.downloads.errors import (
    DownloadCancelled,
    DownloadPaused,
    DownloadRecordNotFound,
    DownloadRecoveryRequired,
    DownloadResponseRejected,
    DownloadUnavailable,
)
from manga_to_kindle.application.downloads.retry_policy import decide_retry
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.domain.downloads import DownloadPage, DownloadPageState
from manga_to_kindle.domain.providers import MangaProvider, ProviderPageReference
from manga_to_kindle.infrastructure.downloads.page_store import (
    MAX_COMPRESSED_BYTES,
    PageStore,
)
from manga_to_kindle.infrastructure.downloads.transport import (
    CancellationSignal,
    DownloadTransport,
    TransportFailure,
)
from manga_to_kindle.infrastructure.network.url_policy import (
    ExternalUrlPolicy,
    ValidatedDestination,
)
from manga_to_kindle.infrastructure.persistence.download_repository import DownloadRepository

MAX_GLOBAL_TRANSFERS = 2
CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 30.0

type ProgressCallback = Callable[[int, int | None, str], None]

_GLOBAL_TRANSFER_SLOTS = threading.BoundedSemaphore(MAX_GLOBAL_TRANSFERS)
_GLOBAL_RATE_LOCK = threading.Lock()
_GLOBAL_NEXT_REQUEST_BY_PROVIDER: dict[str, float] = {}


@dataclass(frozen=True, slots=True)
class DownloadRunResult:
    completed_pages: int
    total_pages: int | None
    failed_pages: int
    state: DownloadState


class DownloadQueue:
    def __init__(
        self,
        repository: DownloadRepository,
        transport: DownloadTransport,
        page_store: PageStore,
        url_policy: ExternalUrlPolicy,
        signals: DownloadControlSignals | None = None,
    ) -> None:
        self._repository = repository
        self._transport = transport
        self._page_store = page_store
        self._url_policy = url_policy
        self.signals = signals or DownloadControlSignals()

    def execute(
        self,
        *,
        job_id: UUID,
        provider: MangaProvider,
        references: Mapping[tuple[UUID, str], ProviderPageReference],
        cancellation: CancellationSignal,
        report_progress: ProgressCallback | None = None,
        user_parallelism: int = MAX_GLOBAL_TRANSFERS,
        provider_parallelism: int = MAX_GLOBAL_TRANSFERS,
    ) -> DownloadRunResult:
        snapshot = self._repository.get(job_id)
        if snapshot is None:
            raise DownloadRecordNotFound("O trabalho não foi encontrado.")
        capabilities = provider.capabilities
        if (
            provider.provider_id != snapshot.job.provider_id
            or capabilities.simulated
            or capabilities.requires_authentication
            or not capabilities.page_references
            or not capabilities.download_enabled
        ):
            raise DownloadUnavailable("A fonte não está autorizada para download local.")
        if snapshot.job.cancel_requested:
            if snapshot.job.state in {
                DownloadState.QUEUED,
                DownloadState.RUNNING,
                DownloadState.PAUSED,
                DownloadState.INTERRUPTED,
            }:
                self._repository.set_job_state(job_id, DownloadState.CANCELLED)
                cancelled = self._repository.get(job_id)
                if cancelled is None:
                    raise DownloadRecordNotFound("O trabalho não foi encontrado.")
                return DownloadRunResult(
                    cancelled.job.progress,
                    cancelled.job.total,
                    sum(page.state is DownloadPageState.FAILED for page in cancelled.pages),
                    cancelled.job.state,
                )

        ready_pages = tuple(
            page for page in snapshot.pages if page.state is not DownloadPageState.COMPLETE
        )
        resolved_references: dict[UUID, ProviderPageReference] = {}
        validated_destinations: dict[UUID, ValidatedDestination] = {}
        for page in ready_pages:
            reference = references.get((page.chapter_id, page.source_page_id))
            if reference is None:
                raise DownloadUnavailable("A referência de uma página não está mais disponível.")
            if reference.simulated:
                raise DownloadUnavailable("Referências de demonstração não podem ser baixadas.")
            validated_destinations[page.id] = self._url_policy.validate(
                reference.destination,
                allowed_hosts=capabilities.allowed_hosts,
                allowed_ports=capabilities.allowed_ports,
                allowed_schemes=capabilities.allowed_schemes,
            )
            resolved_references[page.id] = reference

        if snapshot.job.state is DownloadState.QUEUED:
            self._repository.set_job_state(job_id, DownloadState.RUNNING)
        elif snapshot.job.state in {DownloadState.PAUSED, DownloadState.INTERRUPTED}:
            raise DownloadUnavailable(
                "Retome o trabalho explicitamente antes de iniciar novas páginas."
            )
        elif snapshot.job.state is not DownloadState.RUNNING:
            return DownloadRunResult(
                snapshot.job.progress,
                snapshot.job.total,
                sum(page.state is DownloadPageState.FAILED for page in snapshot.pages),
                snapshot.job.state,
            )

        limit = min(
            MAX_GLOBAL_TRANSFERS,
            max(1, user_parallelism),
            max(1, provider_parallelism),
        )
        report = report_progress or (lambda _completed, _total, _stage: None)
        shared_cancel = _CombinedCancellation(
            cancellation,
            self.signals.cancel_event(job_id),
        )
        with ThreadPoolExecutor(max_workers=limit, thread_name_prefix="download-page") as pool:
            futures: list[Future[bool]] = [
                pool.submit(
                    self._process_page,
                    job_id,
                    page,
                    resolved_references[page.id],
                    validated_destinations[page.id],
                    provider.provider_id,
                    capabilities.requests_per_minute,
                    shared_cancel,
                )
                for page in ready_pages
            ]
            for future in as_completed(futures):
                try:
                    page_completed = future.result()
                except DownloadCancelled:
                    continue
                if page_completed:
                    current = self._repository.get(job_id)
                    if current is not None:
                        completed = current.job.progress
                        report(completed, current.job.total, f"Página {completed} concluída")

        current = self._repository.get(job_id)
        if current is None:
            raise DownloadRecordNotFound("O trabalho não foi encontrado.")
        if self.signals.cancel_event(job_id).is_set():
            self._repository.set_job_state(job_id, DownloadState.CANCELLED)
        elif cancellation.cancelled and current.job.state is DownloadState.RUNNING:
            self._repository.set_job_state(job_id, DownloadState.INTERRUPTED)
        elif (
            current.job.state is DownloadState.RUNNING
            and any(page.state is DownloadPageState.FAILED for page in current.pages)
        ):
            self._repository.set_job_state(
                job_id,
                DownloadState.FAILED,
                error_code="PAGE_DOWNLOAD_FAILED",
            )
        final = self._repository.get(job_id)
        if final is None:
            raise DownloadRecordNotFound("O trabalho não foi encontrado.")
        return DownloadRunResult(
            final.job.progress,
            final.job.total,
            sum(page.state is DownloadPageState.FAILED for page in final.pages),
            final.job.state,
        )

    def _process_page(
        self,
        job_id: UUID,
        page: DownloadPage,
        reference: ProviderPageReference,
        destination: ValidatedDestination,
        provider_id: str,
        requests_per_minute: int | None,
        cancellation: CancellationSignal,
    ) -> bool:
        pause_event = self.signals.pause_event(job_id)
        if pause_event.is_set() or cancellation.cancelled:
            return False
        if page.next_attempt_at is not None:
            remaining = (page.next_attempt_at - datetime.now(UTC)).total_seconds()
            while remaining > 0:
                if pause_event.is_set() or cancellation.cancelled:
                    return False
                cancellation.wait(min(remaining, 0.1))
                remaining = (page.next_attempt_at - datetime.now(UTC)).total_seconds()
        for _ in range(4):
            if pause_event.is_set() or cancellation.cancelled:
                return False
            if not _acquire_global_slot(cancellation):
                return False
            try:
                if not self._wait_for_rate(provider_id, requests_per_minute, cancellation):
                    return False
                if pause_event.is_set() or cancellation.cancelled:
                    return False
                current_page = self._repository.begin_page_attempt(job_id, page.id)
                self._repository.set_page_temporary_path(
                    job_id,
                    page.id,
                    self._page_store.temporary_path_for(job_id, page.id),
                )
                try:
                    return self._transfer_page(
                        job_id,
                        current_page,
                        reference,
                        destination,
                        cancellation,
                        pause_event,
                    )
                except _HttpFailure as failure:
                    if self._record_retry_or_failure(
                        job_id,
                        current_page,
                        failure,
                        failure.headers,
                        cancellation,
                    ):
                        continue
                    return False
                except TransportFailure as failure:
                    if self._record_retry_or_failure(
                        job_id,
                        current_page,
                        failure,
                        {},
                        cancellation,
                    ):
                        continue
                    return False
                except (TimeoutError, ConnectionError, OSError):
                    transient_failure = TransportFailure("NETWORK_TRANSIENT", retryable=True)
                    if self._record_retry_or_failure(
                        job_id,
                        current_page,
                        transient_failure,
                        {},
                        cancellation,
                    ):
                        continue
                    return False
                except DownloadCancelled:
                    self._repository.interrupt_page(job_id, page.id)
                    raise
                except DownloadPaused:
                    self._repository.interrupt_page(job_id, page.id)
                    return False
                except DownloadRecoveryRequired:
                    self.signals.pause(job_id)
                    current = self._repository.get(job_id)
                    if current is not None and current.job.state in {
                        DownloadState.RUNNING,
                        DownloadState.PAUSED,
                    }:
                        self._repository.set_job_state(
                            job_id,
                            DownloadState.INTERRUPTED,
                            error_code=DownloadRecoveryRequired.code,
                        )
                    return False
                except Exception as error:
                    code = getattr(error, "code", "DOWNLOAD_FAILED")
                    safe_code = str(code) if _is_safe_code(str(code)) else "DOWNLOAD_FAILED"
                    self._repository.fail_page(job_id, page.id, error_code=safe_code)
                    return False
            finally:
                _GLOBAL_TRANSFER_SLOTS.release()
        return False

    def _transfer_page(
        self,
        job_id: UUID,
        page: DownloadPage,
        reference: ProviderPageReference,
        destination: ValidatedDestination,
        cancellation: CancellationSignal,
        pause_event: threading.Event,
    ) -> bool:
        if pause_event.is_set():
            raise DownloadPaused("O trabalho foi pausado antes da próxima página.")
        if cancellation.cancelled:
            raise DownloadCancelled("O download foi cancelado.")
        response = self._transport.open(
            reference,
            destination=destination,
            connect_timeout_seconds=CONNECT_TIMEOUT_SECONDS,
            read_timeout_seconds=READ_TIMEOUT_SECONDS,
            cancellation=cancellation,
        )
        try:
            destination.assert_connected_address(response.connected_address)
            if response.status_code != 200:
                raise _HttpFailure(response.status_code, response.headers)
            content_encoding = _header(response.headers, "content-encoding")
            if content_encoding is not None and content_encoding.strip().lower() != "identity":
                self._repository.fail_page(job_id, page.id, error_code="CONTENT_ENCODING_REJECTED")
                return False
            declared_size = _content_length(response.headers)
            if declared_size is not None and declared_size > MAX_COMPRESSED_BYTES:
                self._repository.fail_page(job_id, page.id, error_code="IMAGE_TOO_LARGE")
                return False
            content_type = _header(response.headers, "content-type")
            artifact = self._page_store.stage_chunks(
                job_id=job_id,
                page_id=page.id,
                chapter_id=page.chapter_id,
                chunks=response.iter_chunks(),
                content_type=content_type,
                cancellation=cancellation,
            )
        finally:
            try:
                response.close()
            except Exception:
                pass

        if declared_size is not None and declared_size != artifact.image.byte_size:
            self._page_store.discard(artifact, job_id=job_id, page_id=page.id)
            self._repository.fail_page(job_id, page.id, error_code="CONTENT_LENGTH_MISMATCH")
            return False
        self._repository.mark_page_staging(
            job_id,
            page.id,
            temporary_path=artifact.temporary_path,
            final_path=artifact.final_path,
            byte_size=artifact.image.byte_size,
            sha256=artifact.image.sha256,
        )
        try:
            self._page_store.promote(artifact, job_id=job_id, page_id=page.id)
            self._repository.complete_page(job_id, page.id)
        except Exception:
            raise DownloadRecoveryRequired(
                "A página aguarda reconciliação local antes de ser exibida como concluída."
            ) from None
        return True

    def _record_retry_or_failure(
        self,
        job_id: UUID,
        page: DownloadPage,
        failure: TransportFailure | _HttpFailure,
        headers: Mapping[str, str],
        cancellation: CancellationSignal,
    ) -> bool:
        decision = decide_retry(
            attempts_made=page.attempts,
            now=datetime.now(UTC),
            status_code=failure.status_code if isinstance(failure, _HttpFailure) else None,
            retryable_transport_error=(
                failure.retryable if isinstance(failure, TransportFailure) else False
            ),
            headers=headers,
        )
        if not decision.retry or decision.next_attempt_at is None:
            self._repository.fail_page(job_id, page.id, error_code=failure.code)
            return False
        self._repository.schedule_retry(
            job_id,
            page.id,
            next_attempt_at=decision.next_attempt_at,
            error_code=failure.code,
        )
        remaining = decision.delay_seconds or 0.0
        pause = self.signals.pause_event(job_id)
        while remaining > 0:
            if cancellation.cancelled or pause.is_set():
                return False
            interval = min(remaining, 0.1)
            if cancellation.wait(interval):
                return False
            remaining -= interval
        return not cancellation.cancelled and not pause.is_set()

    def _wait_for_rate(
        self,
        provider_id: str,
        requests_per_minute: int | None,
        cancellation: CancellationSignal,
    ) -> bool:
        if requests_per_minute is None:
            return not cancellation.cancelled
        interval = 60.0 / requests_per_minute
        while not cancellation.cancelled:
            with _GLOBAL_RATE_LOCK:
                now = time.monotonic()
                next_allowed = _GLOBAL_NEXT_REQUEST_BY_PROVIDER.get(provider_id, now)
                if now >= next_allowed:
                    _GLOBAL_NEXT_REQUEST_BY_PROVIDER[provider_id] = now + interval
                    return True
                delay = next_allowed - now
            cancellation.wait(min(delay, 0.1))
        return False


class _HttpFailure(TransportFailure):
    def __init__(self, status_code: int, headers: Mapping[str, str]) -> None:
        self.status_code = status_code
        self.headers = headers
        super().__init__(f"HTTP_{status_code}", retryable=False)


class _CombinedCancellation:
    def __init__(self, outer: CancellationSignal, inner: threading.Event) -> None:
        self._outer = outer
        self._inner = inner

    @property
    def cancelled(self) -> bool:
        return self._outer.cancelled or self._inner.is_set()

    def wait(self, timeout_seconds: float) -> bool:
        if self.cancelled:
            return True
        deadline = time.monotonic() + timeout_seconds
        while not self.cancelled:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            self._inner.wait(min(remaining, 0.05))
        return True


def _acquire_global_slot(cancellation: CancellationSignal) -> bool:
    while not cancellation.cancelled:
        if _GLOBAL_TRANSFER_SLOTS.acquire(timeout=0.05):
            return True
    return False


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return next((value for key, value in headers.items() if key.lower() == name), None)


def _content_length(headers: Mapping[str, str]) -> int | None:
    value = _header(headers, "content-length")
    if value is None:
        return None
    try:
        length = int(value, 10)
    except ValueError:
        raise DownloadResponseRejected("Content-Length inválido.") from None
    if length < 0:
        raise DownloadResponseRejected("Content-Length inválido.")
    return length


def _is_safe_code(value: str) -> bool:
    return bool(value) and len(value) <= 64 and value.replace("_", "").isalnum() and value.isupper()
