# Contratos de Atualização — F010

- `RefreshCatalog(manga_id, trigger=manual|scheduled)` resolves F003 provider, calls `get_chapters` only when capability and authorization exist, validates full response using F004, then commits via F008.
- `UpdateScheduler` is inactive by default, runs only while application active, bounds interval by documented minimum, coalesces missed ticks by Manga/provider, and schedules at most one overdue check per item.
- `DetectNewChapters(previous_ids, current_ids)` returns stable ID difference; duplicate IDs dedupe; missing/unreliable IDs disable automatic notice.
- `PersistUpdateResult(snapshot, checks, notices)` commits coherently. Failure/cancel/partial response preserves prior snapshot and does not notify.
- A `ChapterNotice` has no method/side effect to enqueue download or send. User clicks a separate existing flow.
- All I/O in worker; errors are typed and safe; fixture-only mode performs zero network.
