# Contratos de Biblioteca — F008

- Repositories expose typed domain records and query projections; SQLAlchemy models/Session remain inside infrastructure.
- `UnitOfWork` opens one Session per operation/thread, starts transaction explicitly, commits once or rolls back, closes always.
- `LibraryQuery` supports text search, filters, deterministic sort, favorites and paginated/virtualized results as required by spec; never reads file bytes for listing.
- `RegisterAsset` stores relative managed path/checksum/size/type or external reference; validator detects missing file without silently deleting row.
- `RemoveLibraryScope(record_ids, asset_ids, delete_files_confirmed)` requires explicit confirmation; file deletion limited to declared managed assets under root; external paths cannot be deleted by app.
- Batch catalog/import/export/update operations either commit a coherent state or leave recoverable journal/staging for startup reconciliation.
- Migration adapter advances Alembic version only after backup verified and DB integrity/FK check passes.
