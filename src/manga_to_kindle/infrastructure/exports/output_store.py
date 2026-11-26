"""Saída local em staging e publicação sem sobrescrita acidental."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import UUID

from manga_to_kindle.application.exports.ports import StagedOutput as StagedExport
from manga_to_kindle.domain.exports import sanitize_filename_component


class ExportOutputError(OSError):
    code = "EXPORT_OUTPUT_FAILED"


class ExportOutputConflict(ExportOutputError):
    code = "EXPORT_OUTPUT_CONFLICT"


class ExportOutputStore:
    """Gerencia apenas os arquivos de estágio pertencentes a cada exportação."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().absolute()
        self._staging_root = self.root / ".manga-to-kindle-staging"

    def begin(
        self,
        export_id: UUID,
        filename: str,
        *,
        overwrite_confirmed: bool = False,
    ) -> StagedExport:
        self._ensure_root()
        safe_filename = _validate_filename(filename)
        final_path = self.root / safe_filename
        existing_signature: tuple[int, int, int] | None = None
        if final_path.is_symlink() or final_path.is_dir():
            raise ExportOutputError("O destino final não é um arquivo local regular.")
        if final_path.exists():
            if not overwrite_confirmed:
                raise ExportOutputConflict("O arquivo já existe; confirme a substituição.")
            existing_signature = _file_signature(final_path)

        staging_directory = self._staging_root / str(export_id)
        try:
            staging_directory.mkdir(parents=True, exist_ok=False)
        except OSError:
            raise ExportOutputError("Não foi possível preparar a saída temporária.") from None
        return StagedExport(
            id=export_id,
            root=self.root,
            staging_directory=staging_directory,
            staged_path=staging_directory / safe_filename,
            final_path=final_path,
            overwrite_confirmed=overwrite_confirmed,
            existing_signature=existing_signature,
        )

    def publish(self, staged: StagedExport) -> Path:
        root = self._validate_staged(staged)
        if not staged.staged_path.is_file() or staged.staged_path.is_symlink():
            raise ExportOutputError("O pacote temporário não foi criado corretamente.")
        current_signature = (
            _file_signature(staged.final_path) if staged.final_path.exists() else None
        )
        if current_signature != staged.existing_signature:
            raise ExportOutputConflict(
                "O destino mudou durante a exportação; confira o arquivo e tente novamente."
            )
        try:
            if staged.existing_signature is None:
                # hard-link creation is atomic and fails if another process created the path.
                os.link(staged.staged_path, staged.final_path)
                staged.staged_path.unlink()
            else:
                if not staged.overwrite_confirmed:
                    raise ExportOutputConflict("A substituição do arquivo não foi confirmada.")
                os.replace(staged.staged_path, staged.final_path)
        except ExportOutputConflict:
            raise
        except OSError:
            raise ExportOutputError("Não foi possível publicar o arquivo de exportação.") from None
        self._remove_staging_directory(staged.staging_directory, root)
        return staged.final_path

    def cleanup(self, staged: StagedExport) -> None:
        root = self._validate_staged(staged, allow_missing=True)
        if staged.staging_directory.exists():
            self._remove_staging_directory(staged.staging_directory, root)

    def rollback_publication(
        self,
        staged: StagedExport,
        expected_signature: tuple[int, int, int],
    ) -> bool:
        """Remove only a file this call published and that has not changed since."""
        if staged.existing_signature is not None:
            return False
        self._validate_staged(staged, allow_missing=True)
        try:
            if (
                staged.final_path.is_symlink()
                or not staged.final_path.is_file()
                or _file_signature(staged.final_path) != expected_signature
            ):
                return False
            staged.final_path.unlink()
            return True
        except OSError:
            return False

    def _ensure_root(self) -> None:
        try:
            root = self.root.resolve(strict=True)
            if self.root.is_symlink() or not root.is_dir():
                raise OSError("A pasta de saída não é um diretório local regular.")
            if self._staging_root.exists() and self._staging_root.is_symlink():
                raise OSError("A pasta temporária da exportação não pode ser link.")
            self._staging_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise ExportOutputError("A pasta de saída não está disponível com segurança.") from None

    def _validate_staged(self, staged: StagedExport, *, allow_missing: bool = False) -> Path:
        try:
            root = self.root.resolve(strict=True)
            stage = staged.staging_directory.resolve(strict=not allow_missing)
            if (
                self.root.is_symlink()
                or staged.root != self.root
                or staged.staging_directory.is_symlink()
                or stage.parent != self._staging_root.resolve(strict=not allow_missing)
                or not stage.is_relative_to(root)
                or staged.final_path.parent != self.root
                or staged.staged_path.parent != staged.staging_directory
            ):
                raise OSError("O estágio não pertence a esta exportação.")
            return root
        except OSError:
            raise ExportOutputError(
                "O caminho temporário da exportação deixou de ser seguro."
            ) from None

    @staticmethod
    def _remove_staging_directory(staging_directory: Path, root: Path) -> None:
        try:
            if staging_directory.is_symlink() or not staging_directory.resolve().is_relative_to(
                root
            ):
                raise OSError("O estágio não pertence à pasta selecionada.")
            shutil.rmtree(staging_directory)
        except OSError:
            raise ExportOutputError(
                "A saída foi preparada, mas o temporário não foi removido."
            ) from None


def _validate_filename(filename: str) -> str:
    if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ExportOutputError("O nome do arquivo contém um caminho não permitido.")
    suffix = Path(filename).suffix.casefold()
    if suffix not in {".epub", ".cbz"}:
        raise ExportOutputError("O formato do arquivo final não é aceito.")
    stem = sanitize_filename_component(Path(filename).stem, fallback="export")
    return f"{stem}{suffix}"


def _file_signature(path: Path) -> tuple[int, int, int]:
    try:
        metadata = path.stat(follow_symlinks=False)
        if path.is_symlink() or not path.is_file():
            raise OSError("O destino não é um arquivo regular.")
        return metadata.st_size, metadata.st_mtime_ns, metadata.st_ino
    except OSError:
        raise ExportOutputError("Não foi possível conferir o arquivo de destino.") from None
