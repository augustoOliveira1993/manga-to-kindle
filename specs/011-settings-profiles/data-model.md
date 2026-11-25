# Modelo de Dados — F011

| Tipo | Dados/regras |
|---|---|
| `DeviceProfile` | stable ID/version/name/model+generation, width/height, grayscale, direction, margins, crop default, optional quality capability; built-in or user-owned. |
| `ProfileSnapshot` | immutable value object copied into each download/import/process/export at start; subsequent edit cannot alter output. |
| `ApplicationPreferences` | active profile ID, theme, max concurrency 1–2, paths for download/export/cache, cache quota/retention. |
| `CacheEntry` | manifest ID/path, regenerable category, size, last access, expiration, in-use and checksum/status. |
| `RestoreDefaultsPreview` | keys/values to change; explicit confirmation token; no content/deletion operation. |
| `DirectoryPreference` | absolute normalized path, purpose, access/created state; changing default is not a move. |

Factory values: Basic 8/10 600×800 portrait/16 grayscale/167 ppi; Basic 10 active default; Paperwhite 10 1072×1448 portrait/16 gray/300 ppi. New profiles default RTL, gray true, margins 0, crop false, quality 90 where applicable, concurrency 2. Custom dimensions max 10,000 each/50 MP; margins 0–40 and positive usable area. Cache 1 GiB/30d; configurable 100 MiB–20 GiB and 1–365 d.

Built-ins cannot be renamed/deleted; custom names unique case-insensitively. Reset preserves library, originals, derivatives, downloads, exports, history, custom profiles, credentials, notifications and logs.
