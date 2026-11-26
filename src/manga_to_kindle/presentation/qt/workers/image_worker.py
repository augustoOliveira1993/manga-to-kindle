"""Adaptadores Qt para varredura, prévia e importação de imagens locais."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from manga_to_kindle.application.images.import_pages import ImportImages
from manga_to_kindle.domain.image_processing import (
    ImageImportPlan,
    ImageImportTarget,
    ImageProcessingProfile,
    ImageTransformOptions,
)
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    ProgressReporter,
)


def make_image_scan_operation(
    importer: ImportImages,
    source_path: Path,
) -> BackgroundOperation:
    def run(cancellation: CancellationToken, report: ProgressReporter) -> ImageImportPlan:
        return importer.preview_source(
            source_path,
            cancellation=cancellation,
            report_progress=report,
        )

    return run


def make_image_preview_operation(
    importer: ImportImages,
    plan: ImageImportPlan,
    relative_path: str,
    profile: ImageProcessingProfile,
    options: ImageTransformOptions,
) -> BackgroundOperation:
    def run(cancellation: CancellationToken, _report: ProgressReporter) -> tuple[bytes, ...]:
        if cancellation.cancelled:
            return ()
        return importer.preview_image(plan, relative_path, profile, options)

    return run


def make_image_import_operation(
    importer: ImportImages,
    plan: ImageImportPlan,
    target: ImageImportTarget,
    *,
    ordered_paths: Sequence[str],
    profile: ImageProcessingProfile,
    options: ImageTransformOptions,
    confirmed_authorization: bool,
) -> BackgroundOperation:
    def run(cancellation: CancellationToken, report: ProgressReporter) -> object:
        return importer.execute(
            plan,
            target,
            confirmed_authorization=confirmed_authorization,
            ordered_paths=ordered_paths,
            profile=profile,
            options=options,
            cancellation=cancellation,
            report_progress=report,
        )

    return run
