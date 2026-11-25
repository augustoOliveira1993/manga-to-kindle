# Modelo de Dados — F009

| Tipo | Campos/regras |
|---|---|
| `SmtpProfile` | profile ID, host/port, TLS mode, sender, username?, exactly one Kindle recipient, credential reference, validation state. Never password. |
| `TransferConsent` | attempt ID, export package ID/hash, exact destination, sender/server, displayed subject/body digest, timestamp, affirmations; one-shot authorization only. |
| `TransferJob` | ID, ExportPackage, hash/size/format, channel web/manual or SMTP, stage, outcome, timestamps, sanitized error. |
| `TransferOutcome` | waiting, sending, cancelled-before-submission, rejected/failure, accepted-by-server, unknown. No device delivery outcome. |
| `TransferAuditSnapshot` | host/port/sender/masked recipient, TLS mode and consent reference for this attempt. No secret/body/attachment. |

Secrets live exclusively in Windows system credential store and are addressed by opaque credential reference. Default history masks recipient. SMTP body/attachment and book content are never copied to DB/log. Export hash is checked against current bytes before confirmation/transmission; repeat after accepted requires full new consent.
