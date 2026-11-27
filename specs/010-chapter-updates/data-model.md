# Modelo de Dados — F010

| Tipo | Conteúdo/regras |
|---|---|
| `UpdatePreference` | enabled default false; per-manga interval; notification preference; provider minimum validated before opt-in. |
| `UpdateCheck` | Manga/provider IDs, start/end, status, result count, typed/sanitized failure, Retry-After and SHA-256 fingerprint da política consultada. |
| `CatalogSnapshot` | F004 snapshot version and ordered stable Chapter IDs with provider chapter ID, replaced atomically only after full validation. |
| `ChapterNotice` | manga/chapter IDs, stable provider chapter ID, title snapshot, first-seen check/time and read timestamp; unique by manga/provider/stable ID. |
| `UpdatePolicySnapshot` | fingerprint derived from capability/evidence revision, documented interval/rate limits and authorization scope; absent evidence disables real check. |

Migration `0010_catalog_updates` adds `source_chapter_id`, `update_preference`, `update_check` and `chapter_notice` to the central SQLite schema. No DownloadJob/TransferJob relationship is created by a notice. If chapter disappears upstream, retain old local record/history/files; this feature does not delete content. The QTimer exists only in the open process and stops on close.
