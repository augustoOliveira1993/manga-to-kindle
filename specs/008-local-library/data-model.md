# Modelo de Dados — F008

## Relações persistentes

| Entidade/tabela conceitual | Campos/constraints principais |
|---|---|
| Manga | stable internal ID; provider/source identity nullable; title required; optional author/language/cover; favorite; timestamps. Unique provider+source identity when present. |
| Chapter | Manga FK; stable provider/source chapter ID; optional number/volume; display title; source sequence and canonical order; import origin; downloaded state projection. Unique source ID per Manga. |
| FileAsset | managed relative path or external location reference, media type, size, checksum, lifecycle (`staged/available/missing/removed`), ownership scope. No content bytes. |
| Page | Chapter FK; stable page ID; unique position; original FileAsset FK; source identity optional. |
| ProcessedPage | Page FK, derivative FileAsset FK, profile snapshot ID, transformation options and output order. |
| DownloadJob/PageAttempt | target IDs, policy snapshot, status, attempt count, deadlines, progress, sanitized error key; unique active job selection. |
| ImageImportJob | target, source fingerprint, state/progress, cancellation/recovery journal; import batch published whole. |
| DeviceProfile/ProfileSnapshot | immutable built-in/custom profile record; each operation retains snapshot/version. |
| Export/ExportPackage | selection/order/profile/direction/grouping/format/destination/hash/validation/status; unique package identity; no automatic send. |
| TransferJob/Consent | one attempt per explicit consent, export/checksum, masked recipient snapshot, SMTP/server stage and outcome; no password/body/attachment. |
| UpdateCheck/ChapterNotice | source/manga identity, timestamp/status/count, stable new chapter IDs, local notice preferences; no auto job/send relation. |

## Integrity and deletion

All FKs enforced per connection; use unique keys to make repeat import/update/download idempotent. Stable IDs never use display index. Media files use checksums and path confinement to managed root; external output is reference-only. Soft status `missing` represents external file absence. Hard delete prompts for exact records and exact app-managed assets; only confirmed managed paths can be removed, and only within selected scope. Foreign-key cascades must not delete export files, source originals, or unrelated manga.

## Migration ownership

F001 defines initial schema/engine/connection config; later F005/F006/F007/F009/F010/F011 add revisions; F008 validates/consolidates aggregate relationships and search queries. Do not rewrite already released revision. Back up before migration; `PRAGMA foreign_key_check`/schema version and integrity after migration; recovery path on failure.
