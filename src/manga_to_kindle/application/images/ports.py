"""Ports between image use cases and local persistence/storage adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from manga_to_kindle.domain.image_processing import (
    ImageImportChapterTarget,
    ImageImportPlan,
    ImageImportResult,
    ImageImportTarget,
    ImageProcessingProfile,
    ImageTransformOptions,
    ScannedImage,
    StagedImagePage,
)


class ImageStorePort(Protocol):
    @property
    def root(self) -> Path: ...

    def begin_batch(self, job_id: UUID) -> Path: ...

    def stage_page(
        self,
        job_id: UUID,
        *,
        page_id: UUID,
        position: int,
        image: ScannedImage,
        original_bytes: bytes,
        processed_bytes: tuple[bytes, ...],
        duplicate_content: bool,
    ) -> StagedImagePage: ...

    def promote_batch(self, job_id: UUID) -> None: ...

    def cleanup(self, job_id: UUID, *, include_final: bool = True) -> None: ...


class ImageImportRepositoryPort(Protocol):
    def list_targets(self) -> tuple[ImageImportChapterTarget, ...]: ...

    def start_job(
        self,
        job_id: UUID,
        plan: ImageImportPlan,
        target: ImageImportTarget,
    ) -> None: ...

    def update_progress(self, job_id: UUID, completed: int) -> None: ...

    def existing_hashes(self, hashes: tuple[str, ...]) -> frozenset[str]: ...

    def publish(
        self,
        job_id: UUID,
        plan: ImageImportPlan,
        target: ImageImportTarget,
        pages: tuple[StagedImagePage, ...],
        profile: ImageProcessingProfile,
        options: ImageTransformOptions,
    ) -> ImageImportResult: ...

    def fail_job(self, job_id: UUID, *, error_code: str, cancelled: bool = False) -> None: ...

    def staging_jobs(self) -> tuple[UUID, ...]: ...

    def mark_interrupted(self, job_id: UUID) -> None: ...
