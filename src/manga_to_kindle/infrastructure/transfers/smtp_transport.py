"""Cliente SMTP TLS com submissão de um único EPUB por tentativa."""

from __future__ import annotations

import hashlib
import smtplib
import ssl
import stat
from collections.abc import Callable
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from manga_to_kindle.domain.transfers import SmtpProfile, SmtpTransportResult, TlsMode, TransferState

MAX_KINDLE_EMAIL_BYTES = 50_000_000
CONNECTION_TIMEOUT_SECONDS = 20


class CancellationPort(Protocol):
    @property
    def cancelled(self) -> bool: ...


class SmtpTransport:
    def test_connection(self, profile: SmtpProfile, password: str | None) -> None:
        try:
            with _connect(profile) as smtp:
                if profile.username is not None:
                    smtp.login(profile.username, password or "")
        except (OSError, smtplib.SMTPException, UnicodeError):
            raise ConnectionError("Falha ao estabelecer a conexão SMTP com TLS.") from None

    def send(
        self,
        *,
        profile: SmtpProfile,
        password: str | None,
        file_path: Path,
        expected_sha256: str,
        expected_size: int,
        cancellation: CancellationPort,
        report_stage: Callable[[str, str], None],
    ) -> SmtpTransportResult:
        try:
            message_bytes = _build_message(
                profile,
                file_path,
                expected_sha256,
                expected_size,
            )
        except _PayloadTooLarge:
            return SmtpTransportResult(
                TransferState.FAILED_BEFORE_SUBMISSION,
                error_code="MESSAGE_LIMIT_EXCEEDED",
            )
        except OSError:
            return SmtpTransportResult(
                TransferState.FAILED_BEFORE_SUBMISSION,
                error_code="ARTIFACT_UNAVAILABLE",
            )
        except ValueError:
            return SmtpTransportResult(
                TransferState.FAILED_BEFORE_SUBMISSION,
                error_code="ARTIFACT_CHANGED",
            )

        if cancellation.cancelled:
            return SmtpTransportResult(TransferState.CANCELLED_BEFORE_SUBMISSION)

        submitting_data = False
        smtp: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            report_stage("tls", "Negociando TLS validado")
            smtp = _connect(profile)
            size_option = smtp.esmtp_features.get("size", "").strip()
            size_limit = int(size_option) if size_option.isascii() and size_option.isdecimal() else 0
            if size_limit and len(message_bytes) > size_limit:
                return SmtpTransportResult(
                    TransferState.FAILED_BEFORE_SUBMISSION,
                    error_code="MESSAGE_LIMIT_EXCEEDED",
                )

            if cancellation.cancelled:
                return SmtpTransportResult(TransferState.CANCELLED_BEFORE_SUBMISSION)
            if profile.username is not None:
                if password is None:
                    return SmtpTransportResult(
                        TransferState.FAILED_BEFORE_SUBMISSION,
                        error_code="CREDENTIAL_MISSING",
                    )
                report_stage("authenticating", "Autenticando após TLS")
                smtp.login(profile.username, password)

            if cancellation.cancelled:
                return SmtpTransportResult(TransferState.CANCELLED_BEFORE_SUBMISSION)
            report_stage("envelope", "Validando remetente e destino no servidor")
            options = (f"SIZE={len(message_bytes)}",) if smtp.has_extn("size") else ()
            code, _response = smtp.mail(profile.sender, options)
            if code < 200 or code >= 300:
                return _response_result(code)
            code, _response = smtp.rcpt(profile.recipient)
            if code < 200 or code >= 300:
                return _response_result(code)
            if cancellation.cancelled:
                return SmtpTransportResult(TransferState.CANCELLED_BEFORE_SUBMISSION)

            report_stage("transmitting", "Transmitindo o EPUB autorizado")
            submitting_data = True
            code, _response = smtp.data(message_bytes)
            submitting_data = False
            if 200 <= code < 300:
                return SmtpTransportResult(TransferState.ACCEPTED_BY_SMTP, smtp_code=code)
            return _response_result(code)
        except smtplib.SMTPDataError as error:
            return _response_result(error.smtp_code)
        except smtplib.SMTPResponseException as error:
            return _response_result(error.smtp_code)
        except (smtplib.SMTPServerDisconnected, OSError, UnicodeError):
            if submitting_data:
                return SmtpTransportResult(
                    TransferState.UNKNOWN,
                    error_code="SMTP_RESULT_UNKNOWN",
                )
            return SmtpTransportResult(
                TransferState.FAILED_BEFORE_SUBMISSION,
                error_code="SMTP_CONNECTION_FAILED",
            )
        except smtplib.SMTPException:
            if submitting_data:
                return SmtpTransportResult(
                    TransferState.UNKNOWN,
                    error_code="SMTP_RESULT_UNKNOWN",
                )
            return SmtpTransportResult(
                TransferState.FAILED_BEFORE_SUBMISSION,
                error_code="SMTP_PROTOCOL_FAILED",
            )
        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except (OSError, smtplib.SMTPException):
                    try:
                        smtp.close()
                    except OSError:
                        pass


def estimate_message_size(file_size: int, filename: str) -> int:
    if file_size <= 0:
        return 0
    encoded_chars = 4 * ((file_size + 2) // 3)
    line_break_bytes = 2 * ((encoded_chars + 75) // 76)
    header_and_body_allowance = 8192 + (len(filename.encode("utf-8")) * 3)
    return encoded_chars + line_break_bytes + header_and_body_allowance


class _PayloadTooLarge(ValueError):
    pass


def _build_message(
    profile: SmtpProfile,
    file_path: Path,
    expected_sha256: str,
    expected_size: int,
) -> bytes:
    try:
        if file_path.is_symlink():
            raise ValueError("link")
        resolved = file_path.resolve(strict=True)
        if resolved != file_path:
            raise ValueError("path")
        metadata = file_path.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != expected_size:
            raise ValueError("size")
        if estimate_message_size(expected_size, file_path.name) > MAX_KINDLE_EMAIL_BYTES:
            raise _PayloadTooLarge
        payload = file_path.read_bytes()
    except FileNotFoundError:
        raise OSError("missing") from None
    if len(payload) != expected_size or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("changed")

    message = EmailMessage()
    message["From"] = profile.sender
    message["To"] = profile.recipient
    message["Subject"] = file_path.stem
    message.set_content("Documento EPUB enviado pelo Manga to Kindle.")
    message.add_attachment(
        payload,
        maintype="application",
        subtype="epub+zip",
        filename=file_path.name,
    )
    encoded = message.as_bytes(policy=message.policy.clone(linesep="\r\n"))
    if len(encoded) > MAX_KINDLE_EMAIL_BYTES:
        raise _PayloadTooLarge
    return encoded


def _response_result(code: int) -> SmtpTransportResult:
    if 400 <= code < 500:
        return SmtpTransportResult(TransferState.REJECTED_TEMPORARY, smtp_code=code)
    if 500 <= code < 600:
        return SmtpTransportResult(TransferState.REJECTED_PERMANENT, smtp_code=code)
    return SmtpTransportResult(
        TransferState.FAILED_BEFORE_SUBMISSION,
        smtp_code=code,
        error_code="SMTP_UNEXPECTED_RESPONSE",
    )


def _connect(profile: SmtpProfile) -> smtplib.SMTP:
    context = ssl.create_default_context()
    if profile.tls_mode is TlsMode.IMPLICIT:
        smtp: smtplib.SMTP = smtplib.SMTP_SSL(
            profile.host, profile.port, timeout=CONNECTION_TIMEOUT_SECONDS, context=context,
        )
    else:
        smtp = smtplib.SMTP(profile.host, profile.port, timeout=CONNECTION_TIMEOUT_SECONDS)
    try:
        smtp.ehlo_or_helo_if_needed()
        if profile.tls_mode is TlsMode.STARTTLS:
            smtp.starttls(context=context)
            smtp.ehlo_or_helo_if_needed()
    except Exception:
        smtp.close()
        raise
    return smtp
