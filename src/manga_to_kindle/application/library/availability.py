"""Regras determinísticas de disponibilidade local do capítulo."""

from __future__ import annotations

from dataclasses import dataclass

from manga_to_kindle.domain.library import AvailabilityState


@dataclass(frozen=True, slots=True)
class AvailabilityEvidence:
    page_count: int
    expected_download_count: int | None
    complete_download: bool
    complete_import: bool
    missing_file: bool = False
    altered_file: bool = False
    active_progress: int = 0


def classify_availability(evidence: AvailabilityEvidence) -> AvailabilityState:
    if evidence.altered_file:
        return AvailabilityState.ALTERED
    if evidence.missing_file:
        return AvailabilityState.MISSING
    if (
        evidence.complete_download
        and evidence.expected_download_count is not None
        and evidence.expected_download_count > 0
        and evidence.page_count >= evidence.expected_download_count
    ):
        return AvailabilityState.DOWNLOADED
    if evidence.complete_import and evidence.page_count > 0:
        return AvailabilityState.IMPORTED
    if evidence.page_count > 0 or evidence.active_progress > 0:
        return AvailabilityState.PARTIAL
    return AvailabilityState.NOT_DOWNLOADED
