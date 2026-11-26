"""Falhas tipadas de download sem detalhes sensíveis da origem."""

from __future__ import annotations


class DownloadError(RuntimeError):
    code = "DOWNLOAD_FAILED"


class DownloadUnavailable(DownloadError):
    code = "DOWNLOAD_UNAVAILABLE"


class DownloadSelectionInvalid(DownloadError):
    code = "DOWNLOAD_SELECTION_INVALID"


class DuplicateActiveDownload(DownloadError):
    code = "DOWNLOAD_ALREADY_ACTIVE"


class DownloadRecordNotFound(DownloadError):
    code = "DOWNLOAD_NOT_FOUND"


class DownloadCancelled(DownloadError):
    code = "DOWNLOAD_CANCELLED"


class DownloadPaused(DownloadError):
    code = "DOWNLOAD_PAUSED"


class DownloadResponseRejected(DownloadError):
    code = "DOWNLOAD_RESPONSE_REJECTED"


class DownloadImageInvalid(DownloadError):
    code = "DOWNLOAD_IMAGE_INVALID"


class DownloadStorageError(DownloadError):
    code = "DOWNLOAD_STORAGE_FAILED"


class DownloadRecoveryRequired(DownloadError):
    code = "DOWNLOAD_RECOVERY_REQUIRED"


class DownloadIdentityConflict(DownloadError):
    code = "DOWNLOAD_IDENTITY_CONFLICT"
