"""Validação de páginas locais e criação de um plano imutável de pacotes."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from manga_to_kindle.application.exports.errors import ExportPlanRejected
from manga_to_kindle.domain.chapter_ordering import order_chapters
from manga_to_kindle.domain.exports import (
    ExportAsset,
    ExportFormat,
    ExportGrouping,
    ExportPackagePlan,
    ExportPlan,
    ExportRequest,
    ExportSourceChapter,
    PlannedImage,
    sanitize_filename_component,
)


class PlanExport:
    """Confere a seleção e congela a ordem/metadados antes de abrir um destino."""

    def execute(
        self,
        sources: Sequence[ExportSourceChapter],
        request: ExportRequest,
    ) -> ExportPlan:
        by_id = {source.chapter.id: source for source in sources}
        if len(by_id) != len(sources):
            raise ExportPlanRejected("A origem contém identidades de capítulo repetidas.")
        missing = tuple(chapter_id for chapter_id in request.chapter_ids if chapter_id not in by_id)
        if missing:
            raise ExportPlanRejected("Um capítulo selecionado não está mais disponível.")
        selected = tuple(by_id[chapter_id] for chapter_id in request.chapter_ids)
        manga_ids = {source.chapter.manga_id for source in selected}
        manga_titles = {source.manga_title for source in selected}
        if len(manga_ids) != 1 or len(manga_titles) != 1:
            raise ExportPlanRejected("Uma exportação só pode conter capítulos do mesmo mangá.")

        ordered_chapters = order_chapters(tuple(source.chapter for source in selected))
        ordered = tuple(by_id[chapter.id] for chapter in ordered_chapters)
        authors = {source.author for source in ordered}
        if len(authors) > 1:
            raise ExportPlanRejected("Os capítulos selecionados têm autores incompatíveis.")
        languages = {source.language for source in ordered}
        if len(languages) > 1 and request.language is None:
            raise ExportPlanRejected("Escolha um idioma comum para os capítulos selecionados.")
        language = request.language or next(iter(languages))
        if request.format is ExportFormat.EPUB and language is None:
            raise ExportPlanRejected("Escolha um idioma antes de criar o EPUB.")
        covers = {source.cover for source in ordered}
        if len(covers) > 1:
            raise ExportPlanRejected("Os capítulos selecionados não compartilham a mesma capa.")
        cover = next(iter(covers))
        self._validate_assets(ordered, request)

        packages = self._build_packages(ordered, request, cover)
        if not packages:
            raise ExportPlanRejected("A seleção não contém páginas processadas.")
        return ExportPlan(
            id=request.id,
            format=request.format,
            grouping=request.grouping,
            direction=request.direction,
            profile=request.profile,
            output_directory=request.output_directory,
            language=language,
            author=next(iter(authors)),
            max_size_bytes=request.max_size_bytes,
            packages=packages,
        )

    @staticmethod
    def _validate_assets(
        sources: tuple[ExportSourceChapter, ...],
        request: ExportRequest,
    ) -> None:
        all_assets = [
            asset
            for source in sources
            for page in source.pages
            for asset in page.processed
        ]
        covers = [source.cover for source in sources if source.cover is not None]
        if not all_assets:
            raise ExportPlanRejected("A seleção não contém páginas processadas.")
        sizes = {(asset.width, asset.height) for asset in all_assets}
        if len(sizes) != 1:
            raise ExportPlanRejected("As páginas processadas não usam o mesmo perfil de saída.")
        expected_width = request.profile.preferences.get("width")
        expected_height = request.profile.preferences.get("height")
        if (expected_width is None) != (expected_height is None):
            raise ExportPlanRejected("O perfil selecionado contém dimensões incompletas.")
        if expected_width is not None and expected_height is not None:
            if not isinstance(expected_width, int) or not isinstance(expected_height, int):
                raise ExportPlanRejected("As dimensões do perfil selecionado são inválidas.")
            if sizes != {(expected_width, expected_height)}:
                raise ExportPlanRejected("Uma página não corresponde às dimensões do perfil.")
        for asset in (*all_assets, *covers):
            if asset.path.is_symlink() or not asset.path.is_file():
                raise ExportPlanRejected("Uma imagem processada não está disponível localmente.")

    @staticmethod
    def _build_packages(
        sources: tuple[ExportSourceChapter, ...],
        request: ExportRequest,
        cover: ExportAsset | None,
    ) -> tuple[ExportPackagePlan, ...]:
        groups: list[tuple[str | None, tuple[ExportSourceChapter, ...]]]
        if request.grouping is ExportGrouping.CHAPTER:
            groups = [(source.volume, (source,)) for source in sources]
        else:
            grouped: dict[Decimal, list[ExportSourceChapter]] = {}
            for source in sources:
                if source.volume is None:
                    raise ExportPlanRejected(
                        "Agrupamento por volume requer volume conhecido em todos os capítulos."
                    )
                try:
                    volume_number = Decimal(source.volume)
                except InvalidOperation:
                    raise ExportPlanRejected(
                        "Um volume selecionado tem identificador inválido."
                    ) from None
                if not volume_number.is_finite():
                    raise ExportPlanRejected("Um volume selecionado tem identificador inválido.")
                grouped.setdefault(volume_number, []).append(source)
            groups = [
                (str(volume_number), tuple(grouped[volume_number]))
                for volume_number in sorted(grouped)
            ]

        packages: list[ExportPackagePlan] = []
        used_filenames: set[str] = set()
        for volume, group in groups:
            first = group[0]
            if request.grouping is ExportGrouping.VOLUME:
                label = f"Volume {volume}"
            else:
                chapter = first.chapter
                label = chapter.title or (
                    f"Capítulo {chapter.number}" if chapter.number is not None else "Especial"
                )
                if chapter.number is not None and chapter.title is not None:
                    label = f"{chapter.title} ({chapter.number})"
            title = f"{first.manga_title} — {label}"
            filename_stem = sanitize_filename_component(title)
            if filename_stem.casefold() in used_filenames:
                filename_stem = sanitize_filename_component(
                    f"{filename_stem}-{first.chapter.id.hex[:8]}"
                )
            used_filenames.add(filename_stem.casefold())
            planned_pages = tuple(
                PlannedImage(source.chapter.id, page.id, page.position, asset)
                for source in group
                for page in source.pages
                for asset in page.processed
            )
            if not planned_pages:
                raise ExportPlanRejected("Um pacote selecionado não contém páginas processadas.")
            packages.append(
                ExportPackagePlan(
                    id=uuid4(),
                    title=title,
                    filename=f"{filename_stem}.{request.format.value}",
                    chapter_ids=tuple(source.chapter.id for source in group),
                    chapter_titles=tuple(
                        (source.chapter.id, _chapter_title(source)) for source in group
                    ),
                    pages=planned_pages,
                    volume=volume,
                    cover=cover,
                    identifier=f"urn:uuid:{uuid4()}",
                )
            )
        return tuple(packages)


def _chapter_title(source: ExportSourceChapter) -> str:
    chapter = source.chapter
    if chapter.title is not None and chapter.number is not None:
        return f"{chapter.title} ({chapter.number})"
    if chapter.title is not None:
        return chapter.title
    if chapter.number is not None:
        return f"Capítulo {chapter.number}"
    return "Capítulo especial"
