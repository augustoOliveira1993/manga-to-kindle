# Plano de Implementação: F011 — Configurações e Perfis

**Branch**: `011-settings-profiles` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e constituição

Gerenciar perfis internos imutáveis, perfis customizados e preferências gerais; validar com ranges explicitados, persistir/migrar e restaurar defaults sem perda de conteúdo. Perfis Básico 8ª/10ª: portrait 600×800, 16 gray, 167 ppi; 10ª default. Paperwhite 10ª: 1072×1448, 16 gray, 300 ppi. Revalidar refs oficiais antes de implementação/release. UI PT-BR; código em inglês.

## Arquitetura e integração

`domain.profiles` owns `DeviceProfile`/`ApplicationPreferences`, value validation and immutable snapshots; factory profiles bundled as versioned catalog read-only. `application.settings` handles CRUD, reset summary, validation, and migration; `infrastructure.settings` persists through F001 config + F008 repository/migrations. UI `SettingsPage` consumes view DTO; all filesystem checks/cache scans/migrations run in worker. Save only new operations see profile changes. F005 gets concurrency min(source limit, preference max 2); F006 gets processing snapshot; F007 gets export snapshot; F002 theme config applied only at window create/update.

Dimension: int 1..10000 each, area ≤50 MP, margins 0..40 each and usable area >0; reject not silently fix. Direction RTL/LTR, default RTL. Gray true for factory e-ink; color only when capability supports. Crop false; enable still requires preview/confirm F006. Quality integer 1..100, default 90 only for codecs that expose lossy quality; PNG shows N/A. Concurrency 1..2 default 2. Cache initial 1 GiB / 30 d, allowed 100 MiB..20 GiB and retention 1..365 days; only manifest-owned regenerable files are eligible, expired first then LRU; active/unknown/external/final/source never removed.

Paths absolute normalized Windows/access validation for intended use; missing path create only after confirmation; change path affects new operations only and never moves files. Reset dialog enumerates only specified preferences and does not clear custom profiles/content/credentials/logs/history/cache unless separately specified; cancellation is no-op.

## Modelo, persistência e testes

Custom profile edits use new version/value; in-flight operation snapshot immutable. F001 config invalid values kept for diagnostics and ignored safely, not overwritten. Migrations preserve IDs/custom names/references/history, defaults only for explicitly absent new fields. Cache manifest gives ownership; cleanup verifies root and selected cache item path.

Tests: unit boundary values and invalids; integration restart/migrations; snapshots unaffected by profile mutation; defaults and reset/cancel; path exists/missing/permission/no disk; cache eviction expiry/LRU with fixtures proving durable hashes survive; UI keyboard/light/dark. Manual verification on Win10/11 per spec. Map RF-001–031, RNF-001–006, CS-001–009 in [data-model.md](data-model.md), [contracts/settings.md](contracts/settings.md), [quickstart.md](quickstart.md).

## Dependências e riscos

F001/F002/F005/F006/F007/F008. Risk cache cleanup erroneously deletes durable assets: allowlisted cache manifest and root confinement. Risk generic Paperwhite profile dimension mismatch: generation-specific preset and official revalidation. Quality option not supported: capability-gated N/A. No implementation/tests executed.
