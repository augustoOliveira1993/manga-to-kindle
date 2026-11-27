"""Prévia, confirmação explícita e publicação recuperável de um lote local."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.images.errors import (
    ImageContentRejected,
    ImageImportCancelled,
    ImageImportError,
    ImageLimitExceeded,
    ImageSourceRejected,
    ImageStorageFailure,
    ImageTargetConflict,
)
from manga_to_kindle.application.images.import_source import (
    CancellationSignal,
    ImageDecoder,
    ImageSourceReader,
    ScanImageSource,
)
from manga_to_kindle.application.images.ports import (
    ImageImportRepositoryPort,
    ImageStorePort,
)
from manga_to_kindle.domain.image_processing import (
    MAX_IMAGE_BYTES,
    SUPPORTED_IMAGE_FORMATS,
    ImageImportPlan,
    ImageImportResult,
    ImageImportTarget,
    ImageProcessingProfile,
    ImageSourceFile,
    ImageTransformOptions,
    ScannedImage,
    StagedImagePage,
)

type ProgressCallback = Callable[[int, int, str], None]


class ImportImages:
    def __init__(
        self,
        source_reader: ImageSourceReader,
        decoder: ImageDecoder,
        store: ImageStorePort,
        repository: ImageImportRepositoryPort,
    ) -> None:
        self._source_reader = source_reader
        self._decoder = decoder
        self._store = store
        self._repository = repository
        self._scanner = ScanImageSource(source_reader, decoder)

    def preview_source(
        self,
        source_path: Path,
        *,
        cancellation: CancellationSignal | None = None,
        report_progress: ProgressCallback | None = None,
    ) -> ImageImportPlan:
        return self._scanner.execute(
            source_path,
            cancellation=cancellation,
            report_progress=report_progress,
        )

    def preview_image(
        self,
        plan: ImageImportPlan,
        relative_path: str,
        profile: ImageProcessingProfile,
        options: ImageTransformOptions,
    ) -> tuple[bytes, ...]:
        image = next((item for item in plan.images if item.relative_path == relative_path), None)
        if image is None:
            raise ImageSourceRejected("A imagem selecionada não pertence à prévia atual.")
        data = self._read_and_verify(plan, image)
        return self._decoder.preview(
            data,
            profile,
            options,
            is_double_page=relative_path in options.double_page_paths,
        )

    def execute(
        self,
        plan: ImageImportPlan,
        target: ImageImportTarget,
        *,
        confirmed_authorization: bool,
        ordered_paths: Sequence[str] | None = None,
        profile: ImageProcessingProfile | None = None,
        options: ImageTransformOptions | None = None,
        cancellation: CancellationSignal | None = None,
        report_progress: ProgressCallback | None = None,
    ) -> ImageImportResult:
        if not confirmed_authorization:
            raise ImageSourceRejected("Confirme que tem autorização para processar este conteúdo.")
        selected_profile = profile or ImageProcessingProfile()
        selected_options = options or ImageTransformOptions()
        paths = tuple(ordered_paths or (image.relative_path for image in plan.images))
        if len(paths) != len(plan.images) or set(paths) != {
            image.relative_path for image in plan.images
        }:
            raise ImageSourceRejected("A ordem confirmada não corresponde à prévia.")
        if not selected_options.double_page_paths <= set(paths):
            raise ImageSourceRejected("A divisão menciona uma imagem fora da prévia.")

        job_id = uuid4()
        self._repository.start_job(job_id, plan, target)
        promoted = False
        staged_pages: list[StagedImagePage] = []
        report = report_progress or (lambda _done, _total, _stage: None)
        try:
            self._store.begin_batch(job_id)
            images_by_path = {image.relative_path: image for image in plan.images}
            seen_hashes = set(
                self._repository.existing_hashes(tuple(image.sha256 for image in plan.images))
            )
            for position, relative_path in enumerate(paths):
                _raise_if_cancelled(cancellation)
                image = images_by_path[relative_path]
                original = self._read_and_verify(plan, image)
                extension = Path(image.relative_path).suffix.lower()
                if extension not in SUPPORTED_IMAGE_FORMATS:
                    raise ImageContentRejected("A extensão da imagem não é aceita.")
                processed = self._decoder.transform(
                    original,
                    selected_profile,
                    selected_options,
                    is_double_page=relative_path in selected_options.double_page_paths,
                )
                if len(processed) not in {1, 2}:
                    raise ImageContentRejected("O processamento retornou uma quantidade inválida.")
                staged = self._store.stage_page(
                    job_id,
                    page_id=uuid4(),
                    position=position,
                    image=image,
                    original_bytes=original,
                    processed_bytes=processed,
                    duplicate_content=image.sha256 in seen_hashes,
                    processed_width=selected_profile.width,
                    processed_height=selected_profile.height,
                )
                seen_hashes.add(image.sha256)
                staged_pages.append(staged)
                self._repository.update_progress(job_id, position + 1)
                report(position + 1, len(paths), f"Página {position + 1} de {len(paths)} preparada")
            _raise_if_cancelled(cancellation)
            self._store.promote_batch(job_id)
            promoted = True
            result = self._repository.publish(
                job_id,
                plan,
                target,
                tuple(staged_pages),
                selected_profile,
                selected_options,
            )
            if result.idempotent:
                self._store.cleanup(job_id)
            else:
                self._store.cleanup(job_id, include_final=False)
            return result
        except Exception as error:
            error_code = getattr(error, "code", "IMAGE_IMPORT_FAILED")
            safe_code = (
                str(error_code)
                if str(error_code).isupper()
                and str(error_code).replace("_", "").isalnum()
                and len(str(error_code)) <= 64
                else "IMAGE_IMPORT_FAILED"
            )
            cancelled = isinstance(error, ImageImportCancelled) or (
                cancellation is not None and cancellation.cancelled
            )
            try:
                self._store.cleanup(job_id, include_final=promoted)
            except Exception:
                # A staging job remains visible to startup recovery when cleanup cannot finish.
                raise ImageStorageFailure(
                    "A importação será reconciliada na próxima inicialização."
                ) from None
            self._repository.fail_job(job_id, error_code=safe_code, cancelled=cancelled)
            if isinstance(error, ImageImportError):
                raise
            if safe_code == ImageStorageFailure.code:
                raise ImageStorageFailure(
                    "A pasta local não permitiu finalizar a importação."
                ) from None
            if safe_code == ImageTargetConflict.code:
                raise ImageTargetConflict(str(error)) from None
            raise ImageImportError("Não foi possível concluir a importação local.") from None

    def _read_and_verify(self, plan: ImageImportPlan, image: ScannedImage) -> bytes:
        source_file = ImageSourceFile(
            relative_path=image.relative_path,
            locator=image.locator,
            declared_size=image.byte_size,
        )
        data = self._source_reader.read(plan.source_path, source_file, MAX_IMAGE_BYTES)
        if len(data) > MAX_IMAGE_BYTES:
            raise ImageLimitExceeded("Uma imagem excede o limite de 25 MiB.")
        if len(data) != image.byte_size or hashlib.sha256(data).hexdigest() != image.sha256:
            raise ImageSourceRejected(
                "A imagem mudou depois da prévia; verifique a origem novamente."
            )
        expected_format = SUPPORTED_IMAGE_FORMATS.get(Path(image.relative_path).suffix.lower())
        if expected_format is None:
            raise ImageContentRejected("A extensão da imagem não é aceita.")
        self._decoder.inspect(data, expected_format)
        return data


def _raise_if_cancelled(cancellation: CancellationSignal | None) -> None:
    if cancellation is not None and cancellation.cancelled:
        raise ImageImportCancelled("A importação foi cancelada.")
