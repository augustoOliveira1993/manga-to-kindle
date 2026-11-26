"""Divisão determinística de pacotes em limites de capítulo e página."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.exports.errors import ExportPlanRejected
from manga_to_kindle.domain.exports import (
    ExportPackagePlan,
    ExportPlan,
    PlannedImage,
)

_PACKAGE_OVERHEAD = 16 * 1024
_PAGE_OVERHEAD = 2 * 1024
_CHAPTER_OVERHEAD = 1024


class PartitionExport:
    """Predivide antes de gravar e valida também o tamanho real no writer."""

    def execute(self, plan: ExportPlan) -> ExportPlan:
        limit = plan.max_size_bytes
        if limit is None:
            return plan
        packages = tuple(
            part
            for package in plan.packages
            for part in self._partition(package, limit)
        )
        return replace(plan, packages=packages)

    @classmethod
    def _partition(cls, package: ExportPackagePlan, limit: int) -> tuple[ExportPackagePlan, ...]:
        by_chapter: dict[object, list[PlannedImage]] = {
            chapter_id: [] for chapter_id in package.chapter_ids
        }
        for image in package.pages:
            by_chapter[image.chapter_id].append(image)
        title_by_chapter = dict(package.chapter_titles)
        chunks: list[list[PlannedImage]] = []
        current: list[PlannedImage] = []

        for chapter_id in package.chapter_ids:
            chapter_images = by_chapter[chapter_id]
            if not chapter_images:
                raise ExportPlanRejected("Um capítulo planejado perdeu suas páginas processadas.")
            candidate = [*current, *chapter_images]
            if _estimated_size(package, candidate) <= limit:
                current = candidate
                continue
            if current:
                chunks.append(current)
                current = []
            if _estimated_size(package, chapter_images) <= limit:
                current = list(chapter_images)
                continue

            for page_images in _group_by_page(chapter_images):
                candidate_page = [*current, *page_images]
                if _estimated_size(package, candidate_page) <= limit:
                    current = candidate_page
                    continue
                if current:
                    chunks.append(current)
                    current = []
                if _estimated_size(package, page_images) > limit:
                    raise ExportPlanRejected(
                        "Uma página excede o limite. Aumente o tamanho máximo da exportação."
                    )
                current = list(page_images)
        if current:
            chunks.append(current)
        if not chunks:
            raise ExportPlanRejected("Nenhum pacote coube no limite selecionado.")

        if len(chunks) == 1 and chunks[0] == list(package.pages):
            if _estimated_size(package, chunks[0]) > limit:
                raise ExportPlanRejected(
                    "O arquivo final excede o limite selecionado; aumente o limite."
                )
            return (package,)

        extension = Path(package.filename).suffix
        stem = Path(package.filename).stem
        output: list[ExportPackagePlan] = []
        for part_number, images in enumerate(chunks, start=1):
            included_chapters = tuple(
                chapter_id
                for chapter_id in package.chapter_ids
                if any(image.chapter_id == chapter_id for image in images)
            )
            chapter_titles = tuple(
                (chapter_id, title_by_chapter[chapter_id]) for chapter_id in included_chapters
            )
            output.append(
                replace(
                    package,
                    id=uuid4(),
                    title=f"{package.title} (parte {part_number})",
                    filename=f"{stem}-parte-{part_number:03d}{extension}",
                    chapter_ids=included_chapters,
                    chapter_titles=chapter_titles,
                    pages=tuple(images),
                    identifier=f"urn:uuid:{uuid4()}",
                )
            )
        return tuple(output)


def _estimated_size(package: ExportPackagePlan, images: Sequence[PlannedImage]) -> int:
    try:
        image_bytes = sum(image.asset.path.stat().st_size for image in images)
        cover_bytes = package.cover.path.stat().st_size if package.cover is not None else 4096
    except OSError:
        raise ExportPlanRejected(
            "Uma imagem local deixou de estar disponível para estimativa."
        ) from None
    chapter_count = len({image.chapter_id for image in images})
    return (
        _PACKAGE_OVERHEAD
        + cover_bytes
        + image_bytes
        + len(images) * _PAGE_OVERHEAD
        + chapter_count * _CHAPTER_OVERHEAD
    )


def _group_by_page(images: list[PlannedImage]) -> tuple[tuple[PlannedImage, ...], ...]:
    groups: list[list[PlannedImage]] = []
    for image in images:
        if not groups or groups[-1][0].page_id != image.page_id:
            groups.append([])
        groups[-1].append(image)
    return tuple(tuple(group) for group in groups)
