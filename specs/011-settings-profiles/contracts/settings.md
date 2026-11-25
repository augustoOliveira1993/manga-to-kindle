# Contratos de Configuração — F011

- `ValidateDeviceProfile(candidate) -> ValidationResult` rejects out-of-range dimensions/margins and unsupported quality without silent normalization.
- `UpdateProfile(profile_id, changes)` creates/updates custom profile only; built-ins immutable; changes affect new operations only.
- `CreateProfileSnapshot(profile_id, capability_context) -> ProfileSnapshot` validates applicable options and freezes parameters for a job/export.
- `ResolveConcurrency(user_limit, provider_limit) -> min(1..2, provider)`; unknown provider cannot exceed global F005 ceiling.
- `ValidateDirectory(path, purpose)` checks absolute normalized/access; creation requires confirmation; failure preserves previously saved setting.
- `CleanCache(quota, retention, cache_manifest, cancellation)` selects only manifest-owned preview/thumbnail files, expired first then LRU; no active/unknown/final/source files; report failures truthfully.
- `RestoreDefaults(selection, confirmed)` resets specified settings only; cancelled confirmation leaves all values unchanged.
- `ApplyTheme(light|dark)` updates presentation without recoloring semantic state only by color.
