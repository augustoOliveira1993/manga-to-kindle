# Plano de Implementação: F010 — Atualização de Capítulos

**Branch**: `010-chapter-updates` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e gates

Atualização manual e verificação periódica opcional, somente durante app ativo, com intervalos, limite por fonte, IDs estáveis, histórico/avisos locais. Off por padrão; não baixa/envia automaticamente. B003 mantém nenhuma fonte real habilitada enquanto não houver autorização específica de consulta. A implementação local existe; não há adapter de fonte real aprovado neste checkout.

## Arquitetura

`application.updates` recebe refresh manual ou sinal de scheduler; `QTimer` no controller UI apenas agenda próximo vencimento, nunca faz I/O. Timer dispara aplicação para enfileirar worker, agrupado por mangá/provider e com no máximo uma execução vencida. Ao suspender/voltar/reiniciar, descartar catch-up acumulado e agendar próxima execução; sem timer persistido executando em background após encerrar app.

Provider F003 declara capacidade e autorização de consulta de catálogo separadamente de permissão para download, além de rate limit e intervalo mínimo documentados. F010 exige `get_chapter_catalog` com resposta explicitamente completa. F004 aplica ordenação/IDs/seleção; F010 salva snapshot, UpdateCheck e avisos em transaction única por meio do schema central e mantém F008 lendo os registros. Só IDs estáveis novos após a linha de base geram aviso único. Se provider não fornece ID confiável, não notificar novos itens automaticamente. Snapshot anterior preservado em partial/invalid/error; não deletar capítulo/page removidos pela fonte. F005 queue/ F009 transfer permanecem desconectados das notificações.

## Dados, privacidade e erros

Preference off by default e intervalo efetivo atende ao maior entre configuração da pessoa usuária, mínimo documentado, rate limit e Retry-After. Mensagens PT-BR. Erros persistem estado/horário/contagem/código sanitizado; checks registram somente fingerprint SHA-256 da política, nunca evidência textual/URL/query. As requisições rodam em worker; timer não sobrevive ao fechamento; one-shot check não altera fila de downloads.

```text
domain/updates.py
application/updates/{preferences,refresh_manga_catalog,scheduler}.py
infrastructure/persistence/{update_repository,migrations/versions/0010_catalog_updates}.py
presentation/qt/views/update_settings_view.py
tests/{unit/domain/test_catalog_updates,unit/application/test_periodic_update_scheduler,integration/test_catalog_update_flow,integration/test_update_repository,integration/test_update_safety,ui/test_manual_update_view}.py
```

Testes de clock e provider isolados: refresh manual, alteração/adição/IDs duplicados, renomeação, resposta parcial, indisponibilidade/429/Retry-After, coalescing, opt-out e encerramento. Confirmar zero Job/Transfer criado por aviso e ausência de rede no gate da fixture. Esses testes não validam autorização nem integração com fonte real. Mapear RF-001–033, RNF-001–007, CS-001–010 via [model](data-model.md), [contract](contracts/updates.md), [quickstart](quickstart.md).

## Dependências e riscos

F001/F002/F003/F004/F005/F008. B003 bloqueia queries reais sem autorização de metadados e limites aprovados. IDs estáveis evitam falsos positivos por título/ordem; resposta parcial não substitui snapshot válido; timers atrasados são coalescidos; sem auto-download/send. Testes e resultados estão no [checkpoint](../implementation-checkpoint.md).
