"""Orquestra exportação, validação, publicação atômica e registro local."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from manga_to_kindle.application.exports.errors import ExportError
from manga_to_kindle.application.exports.partition import PartitionExport
from manga_to_kindle.application.exports.plan import PlanExport
from manga_to_kindle.application.exports.ports import (
    CancellationPort,
    CbzValidatorPort,
    EpubValidatorPort,
    ExportRepositoryPort,
    OutputStoreFactoryPort,
    PackageWriterPort,
    ProgressPort,
    StagedOutput,
)
from manga_to_kindle.domain.exports import (
    ExportedArtifact,
    ExportFormat,
    ExportPackagePlan,
    ExportRequest,
    GeneratedPackage,
)


class ExportCancelled(ExportError):
    code = "EXPORT_CANCELLED"


class ExportPackageTooLarge(ExportError):
    code = "EXPORT_PACKAGE_TOO_LARGE"


@dataclass(frozen=True, slots=True)
class ExportResult:
    export_id: str
    output_paths: tuple[Path, ...]
    page_count: int
    total_bytes: int


class CreateExport:
    def __init__(
        self,
        repository: ExportRepositoryPort,
        output_store_factory: OutputStoreFactoryPort,
        epub_writer: PackageWriterPort,
        cbz_writer: PackageWriterPort,
        epub_validator: EpubValidatorPort,
        cbz_validator: CbzValidatorPort,
    ) -> None:
        self._repository = repository
        self._output_store_factory = output_store_factory
        self._epub_writer = epub_writer
        self._cbz_writer = cbz_writer
        self._epub_validator = epub_validator
        self._cbz_validator = cbz_validator

    def execute(
        self,
        request: ExportRequest,
        *,
        cancellation: CancellationPort | None = None,
        report_progress: ProgressPort | None = None,
        overwrite_confirmed: bool = False,
    ) -> ExportResult:
        _raise_if_cancelled(cancellation)
        sources = self._repository.load_sources(request.chapter_ids)
        plan = PlanExport().execute(sources, request)
        plan = PartitionExport().execute(plan)
        store = self._output_store_factory(plan.output_directory)
        staged_outputs: list[StagedOutput] = []
        generated: list[tuple[StagedOutput, GeneratedPackage, ExportPackagePlan]] = []
        published: list[tuple[StagedOutput, tuple[int, int, int]]] = []
        record_created = False
        try:
            self._repository.create(plan)
            record_created = True
            self._repository.set_state(plan.id, "running")
            total_work = sum(len(package.pages) + 1 for package in plan.packages)
            done_work = 0
            page_count = sum(len(package.pages) for package in plan.packages)
            _report(report_progress, 0, total_work, "Preparando exportação local")
            for package_index, package in enumerate(plan.packages, start=1):
                _raise_if_cancelled(cancellation)
                staged = store.begin(
                    package.id,
                    package.filename,
                    overwrite_confirmed=overwrite_confirmed,
                )
                staged_outputs.append(staged)

                def report_package(
                    done: int,
                    _total: int,
                    stage: str,
                    base_done: int = done_work,
                    current_package: int = package_index,
                ) -> None:
                    _report(
                        report_progress,
                        base_done + done,
                        total_work,
                        f"Pacote {current_package} de {len(plan.packages)} · {stage}",
                    )

                writer = (
                    self._epub_writer
                    if plan.format is ExportFormat.EPUB
                    else self._cbz_writer
                )
                receipt = writer.write(
                    plan,
                    package,
                    staged.staged_path,
                    cancellation=cancellation,
                    report_progress=report_package,
                )
                if receipt.package_id != package.id or receipt.path != staged.staged_path:
                    raise ExportError("O writer retornou um artefato de outro pacote.")
                if plan.max_size_bytes is not None and receipt.size_bytes > plan.max_size_bytes:
                    raise ExportPackageTooLarge(
                        "Um arquivo ultrapassou o limite final. Aumente o limite e tente novamente."
                    )
                _raise_if_cancelled(cancellation)
                if plan.format is ExportFormat.EPUB:
                    self._epub_validator.execute(staged.staged_path)
                else:
                    validated_pages = self._cbz_validator.execute(staged.staged_path, package)
                    if validated_pages != len(package.pages):
                        raise ExportError("A validação CBZ encontrou uma quantidade inesperada.")
                generated.append((staged, receipt, package))
                done_work += len(package.pages) + 1
                _report(
                    report_progress,
                    done_work,
                    total_work,
                    f"Pacote {package_index} validado",
                )

            artifacts: list[ExportedArtifact] = []
            output_paths: list[Path] = []
            for position, (staged, receipt, package) in enumerate(generated):
                _raise_if_cancelled(cancellation)
                final_path = store.publish(staged)
                metadata = final_path.stat()
                published.append(
                    (staged, (metadata.st_size, metadata.st_mtime_ns, metadata.st_ino))
                )
                output_paths.append(final_path)
                artifacts.append(
                    ExportedArtifact(
                        package_id=package.id,
                        format=plan.format,
                        path=final_path,
                        sha256=receipt.sha256,
                        size_bytes=receipt.size_bytes,
                        chapter_ids=package.chapter_ids,
                        position=position,
                    )
                )
            _raise_if_cancelled(cancellation)
            self._repository.complete(plan.id, tuple(artifacts))
            return ExportResult(
                str(plan.id),
                tuple(output_paths),
                page_count,
                sum(artifact.size_bytes for artifact in artifacts),
            )
        except Exception as error:
            for staged, signature in reversed(published):
                store.rollback_publication(staged, signature)
            for staged in staged_outputs:
                try:
                    store.cleanup(staged)
                except Exception:
                    pass
            if record_created:
                state = "cancelled" if _is_cancelled(error) else "failed"
                try:
                    self._repository.set_state(plan.id, state, error_code=_safe_error_code(error))
                except Exception:
                    pass
            if _is_cancelled(error):
                raise ExportCancelled("A exportação local foi cancelada.") from None
            raise


def _raise_if_cancelled(cancellation: CancellationPort | None) -> None:
    if cancellation is not None and cancellation.cancelled:
        raise ExportCancelled("A exportação local foi cancelada.")


def _is_cancelled(error: Exception) -> bool:
    return getattr(error, "code", "") in {"EXPORT_CANCELLED", "EPUB_WRITE_CANCELLED"}


def _safe_error_code(error: Exception) -> str:
    candidate = str(getattr(error, "code", "EXPORT_FAILED")).upper()
    return candidate if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", candidate) else "EXPORT_FAILED"


def _report(
    callback: ProgressPort | None,
    completed: int,
    total: int,
    stage: str,
) -> None:
    if callback is not None:
        callback(completed, total, stage)
