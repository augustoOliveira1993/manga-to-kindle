"""Preparação, consentimento e envio SMTP de um único EPUB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from manga_to_kindle.application.transfers.open_manual_flow import (
    ArtifactUnavailable,
    TransferArtifactRepository,
    verify_export_artifact,
)
from manga_to_kindle.application.transfers.ports import (
    MAX_KINDLE_EMAIL_BYTES,
    CancellationPort,
    CredentialMissing,
    CredentialVault,
    SmtpTransportPort,
    estimate_message_size,
)
from manga_to_kindle.domain.transfers import (
    ExportTransferArtifact,
    SmtpProfile,
    SmtpTransportResult,
    TransferState,
)


class TransferPreparationError(RuntimeError):
    code = "TRANSFER_PREPARATION_FAILED"


class TransferConsentExpired(RuntimeError):
    code = "TRANSFER_CONSENT_EXPIRED"


class TransferNotConfirmed(RuntimeError):
    code = "TRANSFER_NOT_CONFIRMED"


class SmtpProfileStore(Protocol):
    def get_profile(self) -> SmtpProfile | None: ...


class TransferHistoryStore(Protocol):
    def has_accepted_attempt(self, artifact_id: UUID) -> bool: ...

    def create_attempt(
        self,
        artifact: ExportTransferArtifact,
        profile: SmtpProfile,
        *,
        consented_at: datetime,
    ) -> UUID: ...

    def update_attempt(
        self,
        transfer_id: UUID,
        state: TransferState,
        stage: str,
        *,
        error_code: str | None = None,
        smtp_code: int | None = None,
    ) -> None: ...


type ProgressReporter = object


@dataclass(frozen=True, slots=True)
class TransferPreview:
    artifact: ExportTransferArtifact
    profile: SmtpProfile
    subject: str
    body: str
    estimated_message_bytes: int
    possible_duplicate: bool


@dataclass(frozen=True, slots=True)
class TransferConsent:
    preview: TransferPreview
    recipient_confirmed: bool
    sender_authorized: bool
    duplicate_acknowledged: bool
    consented_at: datetime


@dataclass(frozen=True, slots=True)
class TransferExecutionResult:
    transfer_id: UUID
    state: TransferState
    smtp_code: int | None = None
    error_code: str | None = None


class PreviewSmtpTransfer:
    def __init__(
        self,
        artifacts: TransferArtifactRepository,
        profiles: SmtpProfileStore,
        history: TransferHistoryStore,
    ) -> None:
        self._artifacts = artifacts
        self._profiles = profiles
        self._history = history

    def execute(self, artifact_id: UUID) -> TransferPreview:
        artifact = self._artifacts.get_artifact(artifact_id)
        if artifact is None:
            raise ArtifactUnavailable("A exportação selecionada não está mais disponível.")
        if artifact.format != "epub" or artifact.path.suffix.casefold() != ".epub":
            raise TransferPreparationError("O envio por e-mail aceita somente EPUB exportado.")
        profile = self._profiles.get_profile()
        if profile is None:
            raise TransferPreparationError("Configure um perfil SMTP antes de enviar por e-mail.")
        verify_export_artifact(artifact)
        estimated_size = estimate_message_size(artifact.size_bytes, artifact.path.name)
        if estimated_size > MAX_KINDLE_EMAIL_BYTES:
            raise TransferPreparationError(
                "O tamanho estimado da mensagem supera o limite documentado do canal por e-mail."
            )
        return TransferPreview(
            artifact=artifact,
            profile=profile,
            subject=artifact.path.stem,
            body="Documento EPUB enviado pelo Manga to Kindle.",
            estimated_message_bytes=estimated_size,
            possible_duplicate=self._history.has_accepted_attempt(artifact.id),
        )


class SendSmtpTransfer:
    def __init__(
        self,
        artifacts: TransferArtifactRepository,
        profiles: SmtpProfileStore,
        history: TransferHistoryStore,
        vault: CredentialVault,
        transport: SmtpTransportPort,
    ) -> None:
        self._artifacts = artifacts
        self._profiles = profiles
        self._history = history
        self._vault = vault
        self._transport = transport

    def execute(
        self,
        consent: TransferConsent,
        *,
        cancellation: CancellationPort,
        report_progress: ProgressReporter,
    ) -> TransferExecutionResult:
        preview = consent.preview
        if not consent.recipient_confirmed or not consent.sender_authorized:
            raise TransferNotConfirmed(
                "Confirme o endereço Kindle e a autorização do remetente para esta tentativa."
            )
        if preview.possible_duplicate and not consent.duplicate_acknowledged:
            raise TransferNotConfirmed("Confirme que aceita uma possível cópia duplicada.")
        if consent.consented_at.tzinfo is None or consent.consented_at > datetime.now(UTC):
            raise TransferNotConfirmed("O horário da confirmação não é válido.")

        artifact = self._artifacts.get_artifact(preview.artifact.id)
        profile = self._profiles.get_profile()
        if artifact != preview.artifact or profile != preview.profile:
            raise TransferConsentExpired(
                "O arquivo ou o perfil mudou depois da confirmação. Revise e confirme novamente."
            )
        has_accepted_attempt = self._history.has_accepted_attempt(preview.artifact.id)
        if has_accepted_attempt and not preview.possible_duplicate:
            raise TransferConsentExpired(
                "O arquivo foi aceito desde a revisão. Revise o aviso de possível duplicata."
            )
        verify_export_artifact(artifact)
        if estimate_message_size(artifact.size_bytes, artifact.path.name) > MAX_KINDLE_EMAIL_BYTES:
            raise TransferPreparationError("A mensagem excede o limite de tamanho configurado.")

        transfer_id = self._history.create_attempt(
            artifact,
            profile,
            consented_at=consent.consented_at,
        )
        if cancellation.cancelled:
            self._history.update_attempt(
                transfer_id,
                TransferState.CANCELLED_BEFORE_SUBMISSION,
                "finished",
            )
            return TransferExecutionResult(
                transfer_id,
                TransferState.CANCELLED_BEFORE_SUBMISSION,
            )

        password: str | None = None
        current_stage = "connecting"
        try:
            if profile.credential_ref is not None:
                try:
                    password = self._vault.get(profile.credential_ref)
                except CredentialMissing:
                    result = SmtpTransportResult(
                        TransferState.FAILED_BEFORE_SUBMISSION,
                        error_code="CREDENTIAL_MISSING",
                    )
                    self._history.update_attempt(
                        transfer_id,
                        result.state,
                        "finished",
                        error_code=result.error_code,
                    )
                    return TransferExecutionResult(
                        transfer_id,
                        result.state,
                        result.smtp_code,
                        result.error_code,
                    )

            def report_stage(stage: str, message: str) -> None:
                nonlocal current_stage
                current_stage = stage
                if stage == "authenticating":
                    state = TransferState.AUTHENTICATING
                elif stage == "transmitting":
                    state = TransferState.TRANSMITTING
                else:
                    state = TransferState.CONNECTING
                self._history.update_attempt(transfer_id, state, stage)
                if callable(report_progress):
                    report_progress(0, None, message)

            result = self._transport.send(
                profile=profile,
                password=password,
                file_path=artifact.path,
                expected_sha256=artifact.sha256,
                expected_size=artifact.size_bytes,
                cancellation=cancellation,
                report_stage=report_stage,
            )
            current_stage = "finished"
        except Exception:
            result = SmtpTransportResult(
                TransferState.UNKNOWN
                if current_stage == "transmitting"
                else TransferState.FAILED_BEFORE_SUBMISSION,
                error_code=(
                    "SMTP_RESULT_UNKNOWN"
                    if current_stage == "transmitting"
                    else "SMTP_OPERATION_FAILED"
                ),
            )
        finally:
            password = None

        self._history.update_attempt(
            transfer_id,
            result.state,
            "finished",
            error_code=result.error_code,
            smtp_code=result.smtp_code,
        )
        if callable(report_progress):
            report_progress(1, 1, _result_message(result.state))
        return TransferExecutionResult(
            transfer_id,
            result.state,
            result.smtp_code,
            result.error_code,
        )


def _result_message(state: TransferState) -> str:
    if state is TransferState.ACCEPTED_BY_SMTP:
        return "Aceito pelo servidor SMTP; entrega ao Kindle não confirmada."
    if state is TransferState.UNKNOWN:
        return (
            "Resultado desconhecido após o início da transmissão; "
            "não houve repetição automática."
        )
    if state is TransferState.CANCELLED_BEFORE_SUBMISSION:
        return "Cancelado antes da submissão da mensagem."
    if state is TransferState.REJECTED_TEMPORARY:
        return "O servidor SMTP recusou temporariamente a mensagem."
    if state is TransferState.REJECTED_PERMANENT:
        return "O servidor SMTP recusou a mensagem."
    return "Não foi possível enviar a mensagem antes da aceitação SMTP."
