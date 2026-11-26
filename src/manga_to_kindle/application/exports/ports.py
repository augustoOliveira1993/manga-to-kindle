"""Portas de infraestrutura utilizadas pelo fluxo de exportação."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from manga_to_kindle.domain.exports import (
    ExportableChapter,
    ExportedArtifact,
    ExportPackagePlan,
    ExportPlan,
    ExportSourceChapter,
    GeneratedPackage,
)


class CancellationPort(Protocol):
    @property
    def cancelled(self) -> bool: ...


type ProgressPort = Callable[[int, int | None, str], None]


class ExportRepositoryPort(Protocol):
    def list_exportable_chapters(self) -> tuple[ExportableChapter, ...]: ...

    def load_sources(self, chapter_ids: tuple[UUID, ...]) -> tuple[ExportSourceChapter, ...]: ...

    def create(self, plan: ExportPlan) -> None: ...

    def set_state(self, export_id: UUID, state: str, *, error_code: str | None = None) -> None: ...

    def complete(self, export_id: UUID, artifacts: tuple[ExportedArtifact, ...]) -> None: ...


@dataclass(frozen=True, slots=True)
class StagedOutput:
    id: UUID
    root: Path
    staging_directory: Path
    staged_path: Path
    final_path: Path
    overwrite_confirmed: bool
    existing_signature: tuple[int, int, int] | None


class OutputStorePort(Protocol):
    def begin(
        self,
        export_id: UUID,
        filename: str,
        *,
        overwrite_confirmed: bool = False,
    ) -> StagedOutput: ...

    def publish(self, staged: StagedOutput) -> Path: ...

    def cleanup(self, staged: StagedOutput) -> None: ...

    def rollback_publication(
        self,
        staged: StagedOutput,
        expected_signature: tuple[int, int, int],
    ) -> bool: ...


class PackageWriterPort(Protocol):
    def write(
        self,
        plan: ExportPlan,
        package: ExportPackagePlan,
        destination: Path,
        *,
        cancellation: CancellationPort | None = None,
        report_progress: Callable[[int, int, str], None] | None = None,
    ) -> GeneratedPackage: ...


class EpubValidatorPort(Protocol):
    def execute(self, path: Path) -> object: ...


class CbzValidatorPort(Protocol):
    def execute(self, path: Path, package: ExportPackagePlan) -> int: ...


class OutputStoreFactoryPort(Protocol):
    def __call__(self, root: Path) -> OutputStorePort: ...
