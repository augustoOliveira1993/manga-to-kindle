# Modelo de Dados — F010

| Tipo | Conteúdo/regras |
|---|---|
| `UpdatePreference` | enabled default false; interval; notification preference; configured minimum explicitly validated. |
| `UpdateCheck` | Manga/provider IDs, start/end, status, result count, typed/sanitized failure, next allowed time. |
| `CatalogSnapshot` | F004 snapshot version and ordered stable Chapter IDs, replaced atomically only after full validation. |
| `ChapterNotice` | manga/chapter IDs, first-seen check ID/time, seen/dismissed status; unique by stable chapter ID. |
| `UpdatePolicySnapshot` | provider capability/evidence revision, documented interval/rate limits, Retry-After deadline; absent evidence disables real check. |

No DownloadJob/TransferJob relationship is created by a notice. If chapter disappears upstream, retain old local record/history/files; this feature does not delete content. Timer state restarts inactive when application closes.
