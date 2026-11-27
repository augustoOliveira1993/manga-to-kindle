# Tarefas de Implementação: F010 — Atualização de Capítulos do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/updates.md], [data-model.md] e constituição.

## Dependências

- Features anteriores: F001–F005 e F008 (contratos/persistência, UI/worker, provider, catálogo, fila e biblioteca).
- Usar IDs estáveis de F003/F004, consulta/retry conforme limites da fonte. Sem download ou envio automático; periodicidade desligada por padrão.
- Gate: sources remotas reais dependem da autorização documentada em F003. Usar fixtures e relógio fake enquanto bloqueadas.

## Fase 1 — Setup

- [x] T001 [P] Persistir período e estado por mangá no esquema central SQLite/Alembic, sem adicionar serviço scheduler externo.; arquivos/componentes: `src/manga_to_kindle/infrastructure/persistence/migrations/versions/0010_catalog_updates.py; src/manga_to_kindle/application/updates/scheduler.py`
- [x] T002 [P] Criar fixtures de versões de catálogo e relógio fake em `tests/fixtures/updates/`.

## Fase 2 — Foundational

- [x] T003 Criar testes de identidade/deduplicação de atualização e estado persistido em `tests/unit/domain/test_catalog_updates.py`.
- [x] T004 Implementar entidades de execução de atualização/novo capítulo e estados em `src/manga_to_kindle/domain/updates.py`.
- [x] T005 Criar testes de repository/migração para histórico de consulta via runner F001 em `tests/integration/test_update_repository.py`.
- [x] T006 Implementar persistência de timestamps, resultado, novos IDs e preferências no runner central em `src/manga_to_kindle/infrastructure/persistence/update_repository.py`.

## Fase 3 — Histórias de usuário

### US1 — Atualizar capítulos manualmente (P1)

**Objetivo**: Como pessoa usuária, quero atualizar o catálogo de um mangá quando eu decidir, para ver capítulos novos sem baixar conteúdo automaticamente.

**Teste independente**: Consultar um catálogo de fixture, atualizar sua lista e conferir a ordenação, IDs, seleção e preservação de dados anteriores quando a fixture falhar.

- [x] T007 [US1] Criar testes do refresh manual com catálogo atualizado, duplicatas, cancelamento e falha que preserva dados válidos em `tests/integration/test_catalog_update_flow.py`.
- [x] T008 [US1] Implementar caso de uso que compara catálogo por ID estável e delega consultas ao provider registry em `src/manga_to_kindle/application/updates/refresh_manga_catalog.py`.
- [x] T009 [US1] Criar testes de disponibilidade do botão manual, bloqueio de fixture e interação de avisos em `tests/ui/test_manual_update_view.py`.
- [x] T010 [US1] Integrar refresh por manga em worker cancelável e não bloqueante à nova tela de atualizações.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/update_settings_view.py; src/manga_to_kindle/presentation/qt/main_window.py`

### US2 — Monitorar em intervalo configurável (P2)

**Objetivo**: Como pessoa usuária, quero ativar a verificação periódica para mangás escolhidos e definir um intervalo, para acompanhar novidades enquanto o Manga to Kindle estiver aberto.

**Teste independente**: Usar relógio e provedor simulados para ativar o monitoramento, avançar o tempo, conferir chamadas no vencimento e verificar que desligar a opção ou encerrar o aplicativo para futuras consultas.

- [x] T011 [US2] Criar testes com relógio fake de intervalo mínimo, desligado por padrão, limite agregado e parada do timer no shutdown em `tests/unit/application/test_periodic_update_scheduler.py; tests/ui/test_manual_update_view.py`.
- [x] T012 [US2] Implementar scheduler leve vinculado ao ciclo de vida F001, iniciado somente com opt-in e usando intervalo validado em `src/manga_to_kindle/application/updates/scheduler.py`.
- [x] T013 [US2] Testar limites por provedor, cancelamento, indisponibilidade e ausência de novas consultas após opt-out em `tests/integration/test_catalog_update_flow.py; tests/unit/application/test_periodic_update_scheduler.py`.
- [x] T014 [US2] Integrar scheduler à preferência, respeitar capabilities/limites do provider e assegurar que não cria jobs nem transferências.; arquivos/componentes: `src/manga_to_kindle/application/updates/scheduler.py; src/manga_to_kindle/presentation/qt/views/update_settings_view.py`

### US3 — Identificar e avisar capítulos novos (P2)

**Objetivo**: Como pessoa usuária, quero receber um aviso local quando um catálogo já conhecido ganhar capítulos com novas identidades, para escolher quais capítulos baixar depois.

**Teste independente**: Carregar uma lista inicial de fixture, depois uma lista com IDs antigos, duplicados e novos; conferir avisos únicos e a ausência de DownloadJob ou envio criado pelo aviso.

- [x] T015 [US3] Criar testes de IDs antigos, duplicados/conflitantes, título/posição alterados, baseline e novos IDs em `tests/unit/domain/test_catalog_updates.py; tests/integration/test_catalog_update_flow.py`.
- [x] T016 [US3] Implementar comparação/detecção de novidade por ID estável e reconciliação em `src/manga_to_kindle/domain/updates.py; src/manga_to_kindle/application/updates/refresh_manga_catalog.py`.
- [x] T017 [US3] Criar testes de avisos locais, leitura e nenhuma ação automática em `tests/ui/test_manual_update_view.py; tests/integration/test_update_safety.py`.
- [x] T018 [US3] Integrar avisos locais com snapshot de título, preferência e persistência sem criar DownloadJob ou envio.; arquivos/componentes: `src/manga_to_kindle/infrastructure/persistence/update_repository.py; src/manga_to_kindle/presentation/qt/views/update_settings_view.py`

### US4 — Revisar estado e controlar notificações (P3)

**Objetivo**: Como pessoa usuária, quero consultar a última verificação e controlar avisos por mangá, para entender se o catálogo está atualizado ou se uma fonte falhou.

**Teste independente**: Consultar histórico de verificações simuladas bem-sucedidas, falhas e limitadas após reabrir o aplicativo; conferir timestamps, estado, contagem e preferência de avisos.

- [x] T019 [US4] Criar testes de histórico de sucesso/falha/limite após reinício e configuração de avisos em `tests/integration/test_update_repository.py`.
- [x] T020 [US4] Implementar tela de estado e controles locais para intervalo/avisos em `src/manga_to_kindle/presentation/qt/views/update_settings_view.py`.

## Fase 4 — Integração

- [x] T021 Integrar consulta por ID do provider a F003/F004 e leitura da biblioteca F008 em `tests/integration/test_catalog_update_flow.py`; os provedores de contrato são doubles locais, sem rede e sem evidenciar fonte real.
- [x] T022 Testar que fechamento, opt-out, cancelamento e falha preservam catálogo e não iniciam download/export/envio em `tests/integration/test_update_safety.py; tests/ui/test_manual_update_view.py`.

## Fase 5 — Polish e validação

- [x] T023 Documentar opt-in, intervalo, respeito a limites e distinção entre aviso/download/envio no quickstart.; arquivos/componentes: `README.md; specs/010-chapter-updates/quickstart.md`
- [x] T024 Executar testes de relógio, duplicatas, desativação e segurança; manter a integração de fonte real como gate sem autorização verificável.; arquivos/componentes: `tests/integration/test_catalog_update_flow.py; tests/integration/test_update_safety.py`

## Dependências e estratégia de execução

- Requer `F001:T017` a `F005:T026` e `F008:T020`. F010 reutiliza catálogo/provider, não implementa crawler/scheduler paralelo.
- US1 funciona primeiro com fixture; US2 só persiste intervalo escolhido. T015–T018 não podem criar job nem automatizar qualquer transferência.
- MVP: US1; monitoramento fica opt-in e pode permanecer bloqueado pela autorização da fonte.

## Rastreabilidade

- RF-001–RF-009: T003–T010; RF-010–RF-018: T011–T014; RF-019–RF-026: T015–T018; RF-027–RF-033: T019–T024.
- RNF-001–RNF-007 e CS-001–CS-010: T003–T024, com consulta desativada por padrão e limites/falhas determinísticos.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F005 e F008. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- As tarefas acima cobrem infraestrutura, testes de contrato local e interface condicionada. Elas não concluem o gate de fonte real: a atualização remota segue indisponível até autorização verificável, limites e capacidade de consulta serem aprovados.
