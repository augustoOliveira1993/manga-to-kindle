# Plano de Implementação: F005 — Downloads

**Branch**: `005-download-queue` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo, bloqueios e conformidade

Fila persistente/resumível com concorrência limitada, timeout/retry, pausa/cancelamento, validação de raster e commit atômico de arquivo + metadata. Após autorização limitada de 2026-11-27, a aplicação conecta seleção explícita de item NDL PDM ao download local confirmado; outras fontes permanecem bloqueadas. Livros não são enviados ou transformados.

## Arquitetura e fluxo de estado

`application.downloads` coordena `DownloadJob`, provider capability F003, seleção/ordem F004, política F011, repositório F008 e storage. Um scheduler cria no máximo 2 transferências simultâneas globalmente e reduz ao mínimo entre esse teto e capacidade/rate limit documentado. Sessions SQLAlchemy são por unidade de trabalho, não compartilhadas entre workers. Worker de página faz stream bounded, valida Content-Type allowlist + assinatura + decodificação Pillow e pixel/bytes, grava `.part` próprio sob staging, fsync se definido pelo FS adapter, valida e move com rename atômico no mesmo volume; depois commita metadados de página. Reconciliador de startup reconhece estado cruzado file/DB.

Timeout conexão 10s e read inactivity 30s; retry em connect transient/408/429/5xx: no máximo três tentativas adicionais com backoff padrão 1/2/4s, limitado a 60s. `Retry-After` válido (segundos/data HTTP) é prazo mínimo e nunca encurtado; inválido/expirado usa backoff. Não repetir restrição, 403/auth, conteúdo ausente/inválido, limite/tipo/destino recusado. Trabalho retry/wait persistido. Reinício marca job interrompido e exige retomar explicitamente, sem tráfego automático.

Pause impede novas páginas e deixa terminar/interrompe página em checkpoint seguro; cancel fecha requests, retém completas e remove/identifica partial apenas do próprio job. Resume pula Page completa validada; bytes partial apenas com capability/validator estável compatível; senão descartar e recomeçar.

## Persistência e segurança

F001 tipos e F008 persistence; F005 persiste tentativa, ordem, estado, prazo e checksum via repositório, nunca cria schema concorrente. Máximo 25 MiB encoded e 50 MP decoded, JPEG/PNG/WEBP; conferir limite streaming antes de confiar em Content-Length. Reutilizar mesmo page ID com arquivo válido; hash igual em IDs diferentes reporta duplicate sem unir/remover. Trabalhos duplicados ativos mesmo provider/chapter/page set são rejeitados/deduplicados. Logs excluem URL/query/header/body.

## Estrutura, testes e riscos

```text
application/downloads/{enqueue,schedule,retry,pause,resume,cancel,recover}.py
domain/downloads/{state,policy,page_result}.py
infrastructure/downloads/{transport,staging,validator,repository}/
presentation/qt/workers/download_worker.py
tests/{unit,integration,security,ui}/downloads/
```

Model/contracts: [data-model.md](data-model.md), [contracts/downloads.md](contracts/downloads.md). Testes com fake HTTP/clock/process crash por cada fronteira, Retry-After, limits, retry eligibility, concurrency, duplicates, checksum, DB/file reconciliation e zero internet. Mapear RF-001–026, RNF-001–008, CS-001–008. Riscos centrais: retry violar policy, dois recursos não commitarem juntos e URL SSRF; limitar conforme provider, journaling/reconcile e F003 fail-closed. Nenhum teste executado.

## Dependências e gates

F001/F002/F003/F004; F008 aporta schema completo; F011 controla concorrência. NDL é autorizada somente para item individual PDM selecionado e confirmado. B003 continua bloqueando fontes/escalas adicionais, não o fluxo NDL limitado. F006 pode importar posteriormente sem usar downloader. Verificações da spec estão em [quickstart.md](quickstart.md).
