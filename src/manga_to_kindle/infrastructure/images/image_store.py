"""Staging e promoção atômica de originais e derivados sob a pasta gerenciada."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from uuid import UUID

from manga_to_kindle.domain.image_processing import (
    SUPPORTED_IMAGE_FORMATS,
    ScannedImage,
    StagedImagePage,
    StagedProcessedImage,
)


class ImageStoreError(RuntimeError):
    code = "IMAGE_STORAGE_FAILED"


class ImageStore:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().absolute()
        self._staging_root = self.root / ".staging"
        self._imports_root = self.root / "imports"

    def begin_batch(self, job_id: UUID) -> Path:
        self._ensure_root()
        stage = self._staging_path(job_id)
        if stage.exists():
            raise ImageStoreError("Já existe uma importação temporária com esse identificador.")
        try:
            stage.mkdir(parents=True, exist_ok=False)
            (stage / "originals").mkdir()
            (stage / "processed").mkdir()
        except OSError:
            self.cleanup(job_id, include_final=False)
            raise ImageStoreError("Não foi possível preparar a importação local.") from None
        return stage

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
        processed_width: int = 600,
        processed_height: int = 800,
    ) -> StagedImagePage:
        if position < 0 or not processed_bytes or len(processed_bytes) > 2:
            raise ImageStoreError("A página contém resultados inválidos.")
        extension = Path(image.relative_path).suffix.lower()
        if extension not in SUPPORTED_IMAGE_FORMATS:
            raise ImageStoreError("A imagem não possui extensão aceita.")
        stage_root = self._staging_path(job_id)
        final_root = self._final_path(job_id)
        staged_original = stage_root / "originals" / f"{position:05d}-{page_id.hex}{extension}"
        final_original = final_root / "originals" / staged_original.name
        self._write_new_file(staged_original, original_bytes)
        staged_processed: list[StagedProcessedImage] = []
        for output_order, data in enumerate(processed_bytes):
            name = f"{position:05d}-{page_id.hex}-{output_order:02d}.png"
            staged_path = stage_root / "processed" / name
            self._write_new_file(staged_path, data)
            staged_processed.append(
                StagedProcessedImage(
                    output_order=output_order,
                    staged_path=staged_path,
                    final_path=final_root / "processed" / name,
                    sha256=hashlib.sha256(data).hexdigest(),
                    width=processed_width,
                    height=processed_height,
                )
            )
        return StagedImagePage(
            page_id=page_id,
            relative_path=image.relative_path,
            position=position,
            staged_original_path=staged_original,
            final_original_path=final_original,
            original_sha256=image.sha256,
            media_type=image.media_type,
            width=image.width,
            height=image.height,
            duplicate_content=duplicate_content,
            processed=tuple(staged_processed),
        )

    def promote_batch(self, job_id: UUID) -> None:
        stage = self._staging_path(job_id)
        final = self._final_path(job_id)
        try:
            self._ensure_root()
            if not stage.is_dir() or final.exists():
                raise OSError("A pasta de importação não está pronta.")
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage, final)
        except OSError:
            raise ImageStoreError("Não foi possível finalizar a gravação local.") from None

    def cleanup(self, job_id: UUID, *, include_final: bool = True) -> None:
        self._ensure_root()
        for candidate in (self._staging_path(job_id), self._final_path(job_id)):
            if candidate == self._final_path(job_id) and not include_final:
                continue
            if not candidate.exists():
                continue
            if candidate.is_symlink() or not candidate.resolve().is_relative_to(self.root):
                raise ImageStoreError("A limpeza saiu da pasta local gerenciada.")
            shutil.rmtree(candidate)

    def _ensure_root(self) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            if self.root.is_symlink():
                raise OSError("Raiz gerenciada não pode ser link.")
            self._staging_root.mkdir(parents=True, exist_ok=True)
            self._imports_root.mkdir(parents=True, exist_ok=True)
            if self._staging_root.is_symlink() or self._imports_root.is_symlink():
                raise OSError("Diretório gerenciado não pode ser link.")
        except OSError:
            raise ImageStoreError("A pasta local de imagens não está disponível.") from None

    def _staging_path(self, job_id: UUID) -> Path:
        return self._staging_root / str(job_id)

    def _final_path(self, job_id: UUID) -> Path:
        return self._imports_root / str(job_id)

    @staticmethod
    def _write_new_file(path: Path, data: bytes) -> None:
        try:
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            raise ImageStoreError("Não foi possível gravar uma imagem local.") from None
