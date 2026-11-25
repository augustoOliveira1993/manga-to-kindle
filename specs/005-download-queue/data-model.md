# Modelo de Dados — F005

| Tipo | Dados/regras |
|---|---|
| `DownloadJob` | Manga/capítulos selecionados por IDs; provider; policy snapshot; status; created/updated; cancel request; total/progress; next attempt. Terminal: complete/cancelled/failed definitivo. |
| `DownloadChapter` | chapter ID, ordem canônica, estado agregado e total conhecido opcional. |
| `DownloadPageResult` | source-qualified page ID, posição, estado, tentativas, bytes, hash, caminho final; conclusão somente após decode + atomic rename + metadata commit. |
| `RetrySchedule` | tentativa atual, prazo mínimo `next_attempt_at`, Retry-After origem e backoff aplicado; persistido e determinístico por clock fake. |
| `StagedArtifact` | job/page IDs, path relativo gerenciado, expected identity, bytes e lifecycle; nunca visível como Page concluída. |
| `ProviderDownloadPolicy` | capability/evidência, destinos permitidos, rate/parallelism, formatos e resume validator; ausência bloqueia o enqueue. |

Limites F005: ≤2 requests globais simultâneos (menor se fonte impuser), connect 10 s/read inactivity 30 s, até 3 retries adicionais, backoff 1/2/4 s com teto 60 s salvo Retry-After que é mínimo inviolável; raster JPEG/PNG/WEBP, ≤25 MiB e ≤50 MP. Arquivo final imutável; duplicatas de bytes entre IDs são informativas, não fundidas.

Persistência segue F001/F008 com FK/unique constraints e transaction per page result. Reconciliador mapeia `.part` sem linha, linha sem arquivo, arquivo final sem linha e checksum inválido em ação segura; jamais remove arquivo externo.
