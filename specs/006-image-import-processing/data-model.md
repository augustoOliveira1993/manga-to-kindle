# Modelo de Dados — F006

| Tipo | Propriedades/regras |
|---|---|
| `ImageImportJob` | source type/path fingerprint, target Manga/Chapter, phase, counts/progress, cancel, result/error; lote só publicado completo. |
| `ImportSourceFingerprint` | path relativo normalizado, file size, checksum; detectar reimport sem usar só nome. |
| `Page` | original local byte-preserved, stable identity/order, file checksum/media type/dimensions. |
| `ProcessedPage` | `page_id`, derivation ID, output order, relative path/hash, dimensions, profile snapshot, options; no original overwrite. |
| `ImageProcessingProfile` | target width/height 600×800, grayscale, margins 0–40 (default 0), crop opt-in, RTL/LTR, double-page opt-in, output PNG. |
| `ImportBatch` | staging manifest, validated entry count/bytes and list of pages/derivatives; published all-or-none or recoverable. |
| `SourcePageRelation` | one original can relate to 1 or 2 derivatives; read order determined by reading direction. |

Input limits: 10,000 zip entries, 5,000 image entries, 25 MiB/image, 2 GiB total image bytes, 50 MP decoded/image. Directories are treated with same per-image/aggregate safety limits. Reimports idempotent only for same normalized identity + checksum; equal bytes under different IDs remain separate.
