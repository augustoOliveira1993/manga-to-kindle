# Contrato de Fila — F005

- `EnqueueDownload(chapter_ids, provider_id)` exige IDs válidos e capability `download_authorized`; sem ela rejeita antes de abrir conexão.
- `DownloadScheduler` garante `active_requests <= min(2, provider_limit, user_limit)`, mantém ordem de leitura independente da conclusão e não cria dois jobs ativos com mesmo provider/capítulo/páginas.
- `DownloadTransport.stream(reference, cancellation, limits)` entrega chunks limitados; HTTPX é adapter opcional depois de B003, fake no teste. Cada destino é validado por F003 antes da conexão e por redirect.
- `DownloadPageWorker` executa request, valida headers/bytes/assinatura/decodificação, staging e rename; atualiza estado progress por sinais para UI. O commit de metadados ocorre após o arquivo passar a validação.
- `Pause` impede novas páginas; `Cancel` impede request/página subsequente e preserva arquivos completos. `Resume` após reinício é ação explícita.
- Retry somente de falha transitória/408/429/5xx dentro da política; não repetir auth/restrição/403/ausência/arquivo inválido. Retry-After válido estabelece horário mínimo.
- Logs usam job/page interno sanitizado, nunca URL, headers, body ou bytes.
