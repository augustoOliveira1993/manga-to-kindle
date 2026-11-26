"""Fixtures pequenas e sem rede para os testes da F005."""

from __future__ import annotations

import threading
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from time import sleep
from uuid import UUID, uuid4

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.providers import (
    NormalizedUrl,
    ProviderCapabilities,
    ProviderPageReference,
)
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.download_repository import DownloadRepository

VALID_PNG = Path(__file__).parent / "fixtures" / "downloads" / "valid.png"
PROVIDER_ID = "authorized-test-provider"


def make_reference(
    page_id: str,
    position: int,
    *,
    host: str = "pages.example.test",
) -> ProviderPageReference:
    return ProviderPageReference(
        source_id=page_id,
        position=position,
        source_reference=page_id,
        destination=normalize_url(f"https://{host}/{page_id}.png"),
    )


class AuthorizedProvider:
    provider_id = PROVIDER_ID

    def __init__(
        self,
        pages_by_chapter: Mapping[UUID, tuple[ProviderPageReference, ...]],
        *,
        allowed_hosts: frozenset[str] = frozenset({"pages.example.test"}),
    ) -> None:
        self._pages_by_chapter = pages_by_chapter
        self._get_pages_calls = 0
        self.capabilities = ProviderCapabilities(
            provider_id=self.provider_id,
            allowed_hosts=allowed_hosts,
            allowed_schemes=frozenset({"https"}),
            metadata=True,
            chapters=True,
            page_references=True,
            download_authorized=True,
            authorization_evidence="https://policy.example.test/downloads",
            authorization_reviewed_on=date(2026, 11, 25),
            authorization_scope="Uso local de conteúdo de teste autorizado",
        )

    @property
    def get_pages_calls(self) -> int:
        return self._get_pages_calls

    def supports(self, url: NormalizedUrl) -> bool:
        return url.host in self.capabilities.allowed_hosts

    def get_manga(self, url: NormalizedUrl) -> Manga:
        raise NotImplementedError

    def get_chapters(self, manga: Manga) -> tuple[Chapter, ...]:
        return manga.chapters

    def get_pages(self, chapter: Chapter) -> tuple[ProviderPageReference, ...]:
        self._get_pages_calls += 1
        return self._pages_by_chapter[chapter.id]


def make_catalog(chapter_count: int = 1) -> CatalogSnapshot:
    manga_id = uuid4()
    chapters = tuple(
        Chapter(
            manga_id=manga_id,
            id=uuid4(),
            position=index,
            number=Decimal(index + 1),
        )
        for index in range(chapter_count)
    )
    manga = Manga(
        id=manga_id,
        title="Catálogo de teste autorizado",
        source_ref="catalog-test-id",
        chapters=chapters,
    )
    return CatalogSnapshot(
        provider_id=PROVIDER_ID,
        source_id="catalog-test-id",
        manga=manga,
        updated_at=datetime.now(UTC),
        simulated=False,
    )


def make_repository(tmp_path: Path, catalog: CatalogSnapshot) -> tuple[
    SQLiteDatabase, DownloadRepository
]:
    database = SQLiteDatabase(tmp_path / "profile" / "library.sqlite3")
    database.initialize()
    CatalogRepository(database).replace(catalog)
    return database, DownloadRepository(database, tmp_path / "profile" / "downloads")


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        headers: Mapping[str, str],
        chunks: Iterable[bytes],
        on_close: object,
        connected_address: str,
        delay_seconds: float = 0,
    ) -> None:
        self.status_code = status_code
        self.headers = dict(headers)
        self.connected_address = connected_address
        self._chunks = tuple(chunks)
        self._on_close = on_close
        self._delay_seconds = delay_seconds

    def iter_chunks(self) -> Iterable[bytes]:
        for chunk in self._chunks:
            if self._delay_seconds:
                sleep(self._delay_seconds)
            yield chunk

    def close(self) -> None:
        if callable(self._on_close):
            self._on_close()


class FakeTransport:
    def __init__(
        self,
        image_bytes: bytes | None = None,
        *,
        statuses: Iterable[int] = (200,),
        headers: Mapping[str, str] | None = None,
        wait_for_two: bool = False,
        delay_seconds: float = 0,
        connected_address: str = "93.184.216.34",
    ) -> None:
        self.image_bytes = image_bytes if image_bytes is not None else VALID_PNG.read_bytes()
        self.statuses = iter(statuses)
        self.headers = dict(headers or {})
        self.wait_for_two = wait_for_two
        self.delay_seconds = delay_seconds
        self.connected_address = connected_address
        self._lock = threading.Lock()
        self._both_open = threading.Event()
        self.opened = threading.Event()
        self.active = 0
        self.max_active = 0
        self.calls: list[tuple[ProviderPageReference, float, float]] = []
        self.open_thread_ids: list[int] = []
        self.destinations: list[object] = []

    def open(
        self,
        reference: ProviderPageReference,
        *,
        destination: object,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        cancellation: object,
    ) -> FakeResponse:
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.calls.append((reference, connect_timeout_seconds, read_timeout_seconds))
            self.destinations.append(destination)
            self.open_thread_ids.append(threading.get_ident())
            self.opened.set()
            if self.active >= 2:
                self._both_open.set()
            status = next(self.statuses, 200)

        def close() -> None:
            with self._lock:
                self.active -= 1

        if self.wait_for_two:
            self._both_open.wait(1)
        response_headers = {"content-type": "image/png", **self.headers}
        if status == 200:
            response_headers.setdefault("content-length", str(len(self.image_bytes)))
        return FakeResponse(
            status_code=status,
            headers=response_headers,
            chunks=(self.image_bytes,),
            on_close=close,
            connected_address=self.connected_address,
            delay_seconds=self.delay_seconds,
        )

    @property
    def both_open(self) -> threading.Event:
        return self._both_open


class NeverCancelled:
    @property
    def cancelled(self) -> bool:
        return False

    def wait(self, timeout_seconds: float) -> bool:
        sleep(timeout_seconds)
        return False
