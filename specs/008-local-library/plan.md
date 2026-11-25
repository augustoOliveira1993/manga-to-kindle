# Plano de Implementação: F008 — Biblioteca Local

**Branch**: `008-local-library` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e propriedade

Consolidar o modelo persistente local de mangas, capítulos, páginas/arquivos, downloads, imports, derivados, exports, transferências, verificações e preferências; prover busca/filtros/favoritos/histórico e exclusão com confirmação/escopo. F001 é owner do bootstrap/engine/schema inicial; F008 estende repositórios e revisões, sem uma segunda engine/session factory/migration system.

## Arquitetura e persistência

**Integração da migração**: F001 possui o único engine/runner Alembic. Revisões específicas de F005–F007 e F009–F011 são criadas junto às respectivas features, quando seus dados surgem; F008 consolida relações, integridade e consultas sobre esse schema, sem adiar migrations necessárias nem criar runner paralelo.

SQLAlchemy 2 typed ORM somente em `infrastructure.persistence`; Alembic é mecanismo único de migrations. Domínio usa IDs e dataclasses; application repositories/unit-of-work ports retornam domain objects/projections. Sessão é mutável e não thread-safe; cada operação worker cria sua Session e a encerra no mesmo worker. Foreign key enforcement on every SQLite connection; migrations use batch rebuild where needed. Use SQLite backup API or validated copied backup before risky upgrade (F012). No DB call in UI thread.

Entidades consolidadas: Manga (provider/source stable IDs, optional metadata, favorite); Chapter (stable ID, volume/number optional, canonical order, history/availability); Page (original file, immutable path/checksum/media/dims/order); ProcessedPage (derivative/profile/options); DownloadJob + page results/attempts/progress/deadline; ImageImportJob; DeviceProfile snapshots; ExportJob/ExportPackage/validation; TransferJob/consent/outcome; UpdateCheck/notification; application config stays in F001 local config unless pref query/filter needs DB. Do not store image bytes, SMTP secret, URL with query, or book content in DB.

File rows store managed relative path, size, hash, media type, lifecycle/availability. Source imports and final output may be outside app area only through explicit user destination; reference them without assuming ownership. Foreign key cascade rules must preserve external files and hard delete only with confirmation and explicit file scope. Removing a DB row cannot delete a file outside managed root. Missing files become `missing` status on scan/query, not schema deletion. Filesystem/DB cross-resource changes journal staging/rename/transaction/recovery.

## Search, ordering, errors

Search case/diacritic insensitive with deterministic order and escaped filter values; sort criteria stable. Index title/source IDs/foreign keys/favorite/update timestamps based on query tests; avoid speculative full-text dependency. Catalog IDs unique within provider/source; duplicate source chapter is idempotent. Deletion dialog enumerates records and exact paths/bytes affected; no cascade beyond selected scope.

## Migrations and tests

Incremental revisions: preserve F001 `0001` immutable; add F008 revisions after predecessor models exist; use transactional/batch migration, backup validation, foreign key check, downgrade strategy only where data-safe. Tests seed temp DB, run from blank and prior schema, restart, check FK, unique keys, search accents/case, history/favorites, missing file and deletion confirmations; inject crash between file rename and DB commit. Trace RF-001–033, RNF-001–008, CS-001–010 to [data-model.md](data-model.md), [contracts/library.md](contracts/library.md), [quickstart.md](quickstart.md).

## Estrutura e dependências

`domain/library`, `application/library`, `infrastructure/persistence/{models,mappings,repositories,unit_of_work,migrations}`, `infrastructure/storage/manifest`, UI projections; tests/unit/integration/security/library. Depends F001–F007. F009/F010/F011 consume persistent records; F012 backs up/upgrades. Risks: ORM entities leak inward, cascades deleting user content, DB references stale after outside move, migrations across worker sessions; enforce typed mappings/port boundary, explicit delete scope, reconcile missing, one session/operation.
