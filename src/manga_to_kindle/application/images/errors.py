"""Falhas de importação com códigos seguros para interface e logs."""

from __future__ import annotations

from manga_to_kindle.domain.image_processing import (
    ImageContentRejected,
    ImageImportCancelled,
    ImageLimitExceeded,
    ImageSourceRejected,
    ImageTargetConflict,
)
from manga_to_kindle.domain.image_processing import (
    ImageProcessingError as ImageImportError,
)

__all__ = [
    "ImageContentRejected",
    "ImageImportCancelled",
    "ImageImportError",
    "ImageLimitExceeded",
    "ImageSourceRejected",
    "ImageStorageFailure",
    "ImageTargetConflict",
]

class ImageStorageFailure(ImageImportError):
    code = "IMAGE_STORAGE_FAILED"
