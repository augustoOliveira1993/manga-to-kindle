# Plano de Implementação: F010 — Atualização de Capítulos

**Branch**: `010-chapter-updates` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e gates

Atualização manual e verificação periódica opcional, somente durante app ativo, com intervalos, limite por fonte, IDs estáveis, histórico/avisos locais. Off por padrão; não baixa/envia automaticamente. B003 mantém nenhuma fonte real habilitada enquanto não houver autorização específica de consulta.

## Arquitetura

`application.updates` recebe refresh manual ou sinal de scheduler; `QTimer` no controller UI apenas agenda próximo vencimento, nunca faz I/O. Timer dispara aplicação para enfileirar worker, agrupado por mangá/provider e com no máximo uma execução vencida. Ao suspender/voltar/reiniciar, descartar catch-up acumulado e agendar próxima execução; sem timer persistido executando em background após encerrar app.

Provider F003 capability `get_chapters` deve documentar consulta metadata, autorização, rate limit, intervalo mínimo, request cost e destino seguro, separadamente de permissão para download. F004 aplica parse/IDs/order/selection; F008 persiste último snapshot, UpdateCheck e notice em transaction única. Só IDs estáveis novos geram aviso único. Se provider não fornece ID confiável, não notificar novos itens automaticamente. Snapshot anterior preservado em partial/invalid/error; não deletar capítulo/page removidos pela fonte. F005 queue/ F009 transfer permanecem fluxos desconectados das notificações.

## Dados, privacidade e erros

Preference off by default e intervalo min atende ao maior entre user config, provider docs e limite do server/Retry-After. Mensagens locales PT-BR. Erros de timeout/unavailable/limit persistem status/time/result count e próxima ação, sem URL/query. As requisições rodam em worker; cancel ao fechar; one-shot check não muda execução pendente de downloads.

```text
domain/updates/{update_check,chapter_notice,policy}.py
application/updates/{check_catalog,scheduler,reconcile_new_chapters}.py
infrastructure/updates/{repository,clock,provider_adapter}.py
presentation/qt/{update_settings,notification_view,workers}/
tests/{unit,integration,ui}/updates/
```

Testes fake clock/provider: manual refresh, change/add/duplicate IDs, reordering/renaming, partial response failure, unavailable/429/Retry-After, suspended clock/coalescing, opt-out and shutdown. Assert zero Job/Transfer created from a notice and no network with fixtures. Mapear RF-001–033, RNF-001–007, CS-001–010 via [model](data-model.md), [contract](contracts/updates.md), [quickstart](quickstart.md).

## Dependências e riscos

F001/F002/F003/F004/F005/F008. B003 blocks real queries absent metadata authorization and limits. Risk of false positive from title/order changes mitigated by stable IDs only; stale/partial response cannot replace last good; bursts coalesced; no auto-download/send. No tests executed.
