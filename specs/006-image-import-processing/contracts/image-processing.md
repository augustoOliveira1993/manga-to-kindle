# Contrato de Imagens — F006

- `PlanImport(source, target, profile) -> ImportPlan` scans/validates complete input within limits before public commit; rejects unsafe archive names/types, encryption, collisions and target chapter conflicts.
- `ImportWorker(plan, cancellation) -> ImportResult` streams/copies original bytes to managed staging, decodes each image, emits progress per image/chapter and publishes batch atomically via repository/storage ports.
- `PreviewPage(original, profile, options) -> PreviewResult` applies EXIF correction to derivative only, composes alpha white, grayscale 8-bit, proportional contain and white margins; deterministic for identical input/options.
- `Crop` and `SplitDoublePage` are explicit option values default false; split requires user-selected page and output ordering (RTL right then left; LTR left then right).
- `OriginalStorage` accepts immutable copy only; `ProcessedPageStorage` writes derivative in distinct path. Neither adapter writes outside managed roots.
- Cancellation/failure removes only known staging files and leaves source/previous published batch untouched.
