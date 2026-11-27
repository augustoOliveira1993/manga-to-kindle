"""One-off catalog access to individual Public Domain Mark items in NDL Next Digital Library."""

from __future__ import annotations

import json
import math
import re
import threading
import time
from collections.abc import Callable, Mapping
from datetime import date
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.providers import (
    AccessRestricted,
    ContentUnavailable,
    NormalizedUrl,
    ProviderCapabilities,
    ProviderPageReference,
    ProviderResponseInvalid,
    ProviderUnavailable,
    RateLimited,
    RedirectRejected,
)
from manga_to_kindle.infrastructure.downloads.transport import TransportFailure
from manga_to_kindle.infrastructure.network.pinned_http_transport import PinnedHttpTransport
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy

NDL_PROVIDER_ID = "ndl-next-digital-library"
NDL_API_HOST = "lab.ndl.go.jp"
NDL_IMAGE_HOST = "dl.ndl.go.jp"
NDL_IMAGE_DELIVERY_HOST = "dss-r4-prod-contents-download.s3.amazonaws.com"
NDL_DOWNLOAD_RATE_LIMIT_PER_MINUTE = 12
NDL_METADATA_MINIMUM_INTERVAL_SECONDS = 60.0
NDL_METADATA_MAX_BYTES = 2 * 1024 * 1024
_ITEM_PATH = re.compile(r"^/dl/book/(?P<pid>[0-9]{1,12})/?$")
_PAGE_SOURCE = re.compile(r"^ndl:(?P<pid>[0-9]{1,12}):(?P<page>[1-9][0-9]{0,4})$")
_PAGE_LIMIT = 10_000
_REVIEW_DATE = date(2026, 11, 27)


class _CancellationProbe:
    def __init__(self, predicate: Callable[[], bool]) -> None:
        self._predicate = predicate

    @property
    def cancelled(self) -> bool:
        return self._predicate()

    def wait(self, timeout_seconds: float) -> bool:
        time.sleep(timeout_seconds)
        return self.cancelled


class NdlProvider:
    """Provides a single user-selected NDL item; it does not discover or monitor catalogs."""

    provider_id = NDL_PROVIDER_ID

    def __init__(
        self,
        transport: PinnedHttpTransport,
        url_policy: ExternalUrlPolicy,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._transport = transport
        self._url_policy = url_policy
        self._monotonic = monotonic
        self._rate_lock = threading.Lock()
        self._last_query_at: float | None = None
        self._page_counts: dict[UUID, tuple[str, int]] = {}
        self._page_counts_lock = threading.Lock()
        self.capabilities = ProviderCapabilities(
            provider_id=self.provider_id,
            allowed_hosts=frozenset(
                {NDL_API_HOST, NDL_IMAGE_HOST, NDL_IMAGE_DELIVERY_HOST}
            ),
            allowed_ports=frozenset({443}),
            allowed_schemes=frozenset({"https"}),
            metadata=True,
            chapters=True,
            page_references=True,
            download_authorized=True,
            authorization_evidence=(
                "NDL Next Digital Library terms identify included materials as Public Domain "
                "Mark; access is limited here to an individual record selected by the user."
            ),
            authorization_reviewed_on=_REVIEW_DATE,
            authorization_scope=(
                "One user-selected NDL item explicitly included in the Next Digital Library "
                "PDM corpus, downloaded locally after explicit selection; no redistribution, "
                "continuous access, or periodic updates."
            ),
            requests_per_minute=NDL_DOWNLOAD_RATE_LIMIT_PER_MINUTE,
            required_attribution=(
                "Fonte: National Diet Library, Next Digital Library. Item indicado como "
                "Public Domain Mark 1.0; preserve the source notice."
            ),
            removal_policy=(
                "Recheck NDL item status before a new download; remove locally stored pages "
                "if the item is withdrawn or no longer marked Public Domain Mark."
            ),
            catalog_query_authorized=True,
            catalog_query_evidence=(
                "NDL API documentation and service terms allow non-continuous API use without "
                "application; continuous use requires contacting NDL."
            ),
            catalog_query_reviewed_on=_REVIEW_DATE,
            catalog_query_scope="One user-initiated metadata lookup for a specific NDL item.",
            periodic_catalog_updates_authorized=False,
        )

    def supports(self, url: NormalizedUrl) -> bool:
        return (
            url.scheme == "https"
            and url.host == NDL_API_HOST
            and url.port == 443
            and _ITEM_PATH.fullmatch(url.path) is not None
            and not url.query
        )

    def get_manga(self, url: NormalizedUrl) -> Manga:
        return self.get_manga_with_cancellation(url, is_cancelled=lambda: False)

    def get_manga_with_cancellation(
        self,
        url: NormalizedUrl,
        *,
        is_cancelled: Callable[[], bool],
    ) -> Manga:
        match = _ITEM_PATH.fullmatch(url.path)
        if not self.supports(url) or match is None:
            raise ContentUnavailable()
        if is_cancelled():
            raise ProviderUnavailable(retryable=False)
        item_id = match.group("pid")
        self._record_catalog_request()
        metadata_url = normalize_url(f"https://{NDL_API_HOST}/dl/api/book/{item_id}")
        destination = self._url_policy.validate(
            metadata_url,
            allowed_hosts=frozenset({NDL_API_HOST}),
            allowed_ports=frozenset({443}),
            allowed_schemes=frozenset({"https"}),
        )
        try:
            response = self._transport.get(
                metadata_url,
                destination=destination,
                connect_timeout_seconds=10.0,
                read_timeout_seconds=20.0,
                cancellation=_CancellationProbe(is_cancelled),
            )
        except TransportFailure as error:
            if is_cancelled():
                raise ProviderUnavailable(retryable=False) from None
            if error.code == "RESPONSE_TOO_LARGE":
                raise ProviderResponseInvalid() from None
            raise ProviderUnavailable(retryable=error.retryable) from None
        try:
            if response.status_code in {301, 302, 303, 307, 308}:
                raise RedirectRejected()
            if response.status_code == 404:
                raise ContentUnavailable()
            if response.status_code in {401, 403, 407}:
                raise AccessRestricted()
            if response.status_code == 429:
                raise RateLimited(_retry_after(response.headers))
            if response.status_code != 200:
                raise ProviderUnavailable()
            if _header(response.headers, "content-encoding") not in {None, "identity"}:
                raise ProviderResponseInvalid()
            if not _is_json_content_type(_header(response.headers, "content-type")):
                raise ProviderResponseInvalid()
            declared_size = _content_length(response.headers)
            if declared_size is not None and declared_size > NDL_METADATA_MAX_BYTES:
                raise ProviderResponseInvalid()
            try:
                body = response.read_limited(NDL_METADATA_MAX_BYTES)
            except TransportFailure as error:
                if is_cancelled():
                    raise ProviderUnavailable(retryable=False) from None
                if error.code == "RESPONSE_TOO_LARGE":
                    raise ProviderResponseInvalid() from None
                raise ProviderUnavailable(retryable=error.retryable) from None
        finally:
            response.close()

        if is_cancelled():
            raise ProviderUnavailable(retryable=False)
        try:
            payload = json.loads(body.decode("utf-8"))
            record = _record_from_payload(payload)
            record_id = _text(record, "id", "pid", "book_id")
            title = _text(record, "title")
            page_count = _positive_page_count(record.get("page", record.get("pages")))
            creator = _optional_text(record.get("responsibility"))
            volume = _optional_text(record.get("volume"))
            if record_id != item_id:
                raise ValueError
        except (UnicodeError, TypeError, ValueError, KeyError, json.JSONDecodeError):
            raise ProviderResponseInvalid() from None

        manga_id = uuid5(NAMESPACE_URL, f"manga-to-kindle:{self.provider_id}:book:{item_id}")
        chapter_id = uuid5(NAMESPACE_URL, f"manga-to-kindle:{self.provider_id}:item:{item_id}")
        chapter = Chapter(
            manga_id=manga_id,
            id=chapter_id,
            position=0,
            title=volume or "Obra completa",
            source_order=0,
            source_chapter_id=item_id,
        )
        manga = Manga(
            id=manga_id,
            title=title,
            author=creator,
            language="ja",
            source_ref=f"ndl:{item_id}",
            chapters=(chapter,),
        )
        with self._page_counts_lock:
            self._page_counts[chapter_id] = (item_id, page_count)
        return manga

    def get_chapters(self, manga: Manga) -> tuple[Chapter, ...]:
        if not manga.source_ref or not manga.source_ref.startswith("ndl:"):
            raise ContentUnavailable()
        with self._page_counts_lock:
            if not any(chapter.id in self._page_counts for chapter in manga.chapters):
                raise ContentUnavailable()
        return manga.chapters

    def get_pages(self, chapter: Chapter) -> tuple[ProviderPageReference, ...]:
        with self._page_counts_lock:
            record = self._page_counts.get(chapter.id)
        if record is None or chapter.source_chapter_id != record[0]:
            raise ContentUnavailable()
        item_id, page_count = record
        return tuple(
            self.restore_page_reference(
                f"ndl:{item_id}",
                f"ndl:{item_id}:{page_number}",
                page_number - 1,
            )
            for page_number in range(1, page_count + 1)
        )

    def restore_page_reference(
        self,
        source_id: str,
        source_page_id: str,
        position: int,
    ) -> ProviderPageReference:
        """Rebuild a persisted page reference without querying NDL again."""
        match = _PAGE_SOURCE.fullmatch(source_page_id)
        if match is None:
            raise ContentUnavailable()
        item_id = match.group("pid")
        page_number = int(match.group("page"))
        if (
            source_id != f"ndl:{item_id}"
            or not 1 <= page_number <= _PAGE_LIMIT
            or position != page_number - 1
        ):
            raise ContentUnavailable()
        return ProviderPageReference(
            source_id=source_page_id,
            position=position,
            source_reference=f"ndl:{item_id}:page:{page_number}",
            destination=normalize_url(
                f"https://{NDL_IMAGE_HOST}/api/iiif/{item_id}/R{page_number:07d}/"
                "full/full/0/default.jpg"
            ),
        )

    def _record_catalog_request(self) -> None:
        now = self._monotonic()
        with self._rate_lock:
            if self._last_query_at is not None:
                remaining = NDL_METADATA_MINIMUM_INTERVAL_SECONDS - (
                    now - self._last_query_at
                )
                if remaining > 0:
                    raise RateLimited(math.ceil(remaining))
            self._last_query_at = now


def _record_from_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError
    candidate = payload.get("book", payload)
    if not isinstance(candidate, dict):
        raise ValueError
    return candidate


def _text(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip() and len(value) <= 1000:
            return value.strip()
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
    raise ValueError


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() and len(value) <= 1000:
        return value.strip()
    raise ValueError


def _positive_page_count(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{1,5}", value.strip()):
        result = int(value.strip())
    else:
        raise ValueError
    if not 1 <= result <= _PAGE_LIMIT:
        raise ValueError
    return result


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return next(
        (value.strip().lower() for key, value in headers.items() if key.lower() == name),
        None,
    )


def _is_json_content_type(value: str | None) -> bool:
    if value is None:
        return False
    media_type = value.split(";", maxsplit=1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def _retry_after(headers: Mapping[str, str]) -> int | None:
    raw = _header(headers, "retry-after")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return max(value, 0)


def _content_length(headers: Mapping[str, str]) -> int | None:
    raw = _header(headers, "content-length")
    if raw is None:
        return None
    if not re.fullmatch(r"[0-9]{1,12}", raw):
        raise ProviderResponseInvalid()
    return int(raw)
