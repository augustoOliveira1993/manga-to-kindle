# Contratos de Transferência — F009

- `CredentialVault` provides `store/get/delete(credential_ref)`; adapter must demonstrate Windows Credential Locker backend. Failure raises typed `VaultUnavailable`, blocks SMTP and never writes secret elsewhere.
- `OpenManualSend(export_id)` validates file/hash and on explicit click opens exact export folder and official URL; it never submits file or reads Amazon page state.
- `ConfirmSmtpTransfer(consent, export_id, profile_id)` revalidates current export checksum and shows exact final metadata before any network call. Consent is scoped to one file, one recipient and one attempt.
- `SmtpTransport` runs off UI thread with TLS validation and finite timeout; test SMTP action cannot transmit content. Only one recipient/message per job.
- Result maps SMTP stage to accepted/rejected/unknown/cancelled. Unknown after DATA/without final response is not retried automatically. Manual retry displays duplicate warning and asks complete confirmation again.
- Logger sanitizes network exception/raw SMTP response and all identifiers before persistence/logging.
