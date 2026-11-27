# Tarefas de Implementação: F005 — Downloads do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/downloads.md](contracts/downloads.md) e constituição.

## Dependências

- Features anteriores: F001–F004 (persistência, UI worker boundary, providers e catálogo/seleção).
- Reutilizar a política de URL F003, IDs e seleção F004, e runner de migrações F001. Fila não cria cliente nem regras de segurança paralelos.
- Gate: testes automatizados usam transporte fake. O download real limitado NDL foi autorizado em 2026-11-27 para item individual PDM após seleção/consentimento; demais fontes exigem autorização e limites próprios.

## Fase 1 — Setup

- [x] T001 [P] Confirmar que HTTPX não está no lock e adiar cliente/adaptador de rede até haver fonte autorizada; nenhuma dependência foi adicionada.
- [x] T002 [P] Criar fixtures binárias pequenas de imagem válida, inválida e acima dos limites em `tests/fixtures/downloads/`.

## Fase 2 — Foundational

- [x] T003 Criar testes de estados e transições persistentes do DownloadJob em `tests/unit/domain/test_download_job.py`.
- [x] T004 Implementar estado/entidade de job e invariantes de transição em `src/manga_to_kindle/domain/downloads.py`.
- [x] T005 Criar testes do transporte fake e validação de política/limite em `tests/unit/infrastructure/test_download_transport.py`.
- [x] T006 Implementar interface de transporte injetável com timeout, cabeçalhos e cancelamento cooperativo em `src/manga_to_kindle/infrastructure/downloads/transport.py`; fake é default em testes.
- [x] T007 Criar testes para persistência idempotente e migração pelo engine Alembic existente em `tests/integration/test_download_repository.py`.
- [x] T008 Implementar repository e revisão Alembic de jobs/páginas parciais em `src/manga_to_kindle/infrastructure/persistence/`; não criar runner próprio.

## Fase 3 — Histórias de usuário

### US1 — Enfileirar e acompanhar capítulos (P1)

**Objetivo**: Como pessoa usuária, quero iniciar o download autorizado dos capítulos selecionados e acompanhar páginas e capítulos, para saber o que está em andamento e o que foi concluído.

**Teste independente**: Selecionar capítulos em uma fixture de teste com transporte isolado, enfileirar o trabalho e conferir estados, limites de concorrência, progresso e ordem final das páginas.

- [x] T009 [US1] Criar testes de concorrência limitada, ordem de página, deduplicação e progresso por capítulo/página em `tests/unit/application/test_download_queue.py`.
- [x] T010 [US1] Implementar fila persistente, limite global configurável, progresso e deduplicação em `src/manga_to_kindle/application/downloads/queue.py`.
- [x] T011 [US1] Criar testes de worker Qt, sinais tipados e responsividade/cancelamento em `tests/integration/test_download_worker.py`.
- [x] T012 [US1] Implementar adaptador worker para fila com progresso em sinais, sem I/O na thread gráfica, em `src/manga_to_kindle/presentation/qt/workers/download_worker.py`.

### US2 — Controlar, pausar e cancelar trabalhos (P1)

**Objetivo**: Como pessoa usuária, quero pausar, retomar ou cancelar um trabalho, para controlar o uso da conexão e interromper uma seleção sem perder arquivos válidos já concluídos.

**Teste independente**: Pausar uma fila em execução, retomá-la, cancelar outra e interromper uma terceira durante o encerramento; verificar transições persistidas, arquivos temporários e páginas já finalizadas.

- [x] T013 [US2] Criar testes de pause/resume/cancel e interrupção durante shutdown em `tests/integration/test_download_controls.py`.
- [x] T014 [US2] Implementar comandos de controle cooperativo e persistência de estado após cada checkpoint seguro em `application/downloads/controls.py`.
- [x] T015 [US2] Criar testes de estado e acessibilidade dos controles em `tests/ui/test_download_controls_view.py`.
- [x] T016 [US2] Integrar início da fila após confirmação explícita, pausa, retomada, restauração das referências e cancelamento à tela Downloads.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/add_manga_view.py; src/manga_to_kindle/presentation/qt/views/downloads_view.py`

### US3 — Recuperar falhas sem arquivos inválidos (P1)

**Objetivo**: Como pessoa usuária, quero que falhas transitórias sejam tratadas com espera e que respostas inválidas sejam descartadas, para não receber arquivos truncados, corrompidos ou fora dos limites.

**Teste independente**: Usar um transporte de teste com timeouts, falhas transitórias, respostas HTTP 429/503, cabeçalho Retry-After, MIME incorreto, conteúdo excessivo, imagem corrompida e interrupção entre gravação e finalização; conferir política de retry e recuperação.

- [x] T017 [US3] Criar testes de timeout, retry/backoff, `Retry-After`, 429/5xx, falha permanente e limites em `tests/unit/application/test_download_retry_policy.py`.
- [x] T018 [US3] Implementar retry limitado que respeita `Retry-After` e rate limits declarados, sem contornar bloqueios, em `application/downloads/retry_policy.py`.
- [x] T019 [US3] Criar testes de MIME, tamanho, decode, hash/duplicata e promoção atômica em `tests/security/test_download_file_validation.py` e `tests/integration/test_atomic_page_save.py`.
- [x] T020 [US3] Implementar validação e staging em temporário, fsync quando aplicável e finalização atômica em `infrastructure/downloads/page_store.py`; arquivos inválidos não entram no catálogo.
- [x] T021 [US3] Criar testes de recuperação após encerramento/reinício e limpeza segura de temporários em `tests/integration/test_download_recovery.py`.
- [x] T022 [US3] Implementar reconciliação de jobs e arquivos pendentes na retomada do aplicativo em `application/downloads/recovery.py`.

## Fase 4 — Integração

- [x] T023 Integrar seleção F004, URL policy F003, estado F001 e worker F002 através de teste com transporte fake em `tests/integration/test_download_flow.py`.
- [x] T024 Verificar ordenação, limites, logs redigidos e nenhuma criação de job por atualizador ou remetente em `tests/security/test_download_boundaries.py`.

## Fase 5 — Polish e validação

- [x] T025 Documentar fluxo local, confirmação, escopo NDL/PDM, limites e recuperação da fila em README e quickstart.; arquivos/componentes: `README.md; specs/005-download-queue/quickstart.md`
- [x] T026 Executar testes focados de retry, cancelamento, segurança de arquivos e reinício; validar o item NDL individual em perfil temporário e registrar manualmente os critérios restantes.; arquivos/componentes: `tests/integration/test_download_flow.py; tests/security/test_download_boundaries.py; specs/005-download-queue/quickstart.md`

## Dependências e estratégia de execução

- Requer `F001:T017`, `F002:T015`, `F003:T015` e `F004:T018`. T009–T012 constituem MVP de fila; testes permanecem isolados e NDL real só opera dentro do escopo autorizado.
- A política de retry (T017–T018) antecede o transporte real. Não executar download externo fora da autorização específica registrada em F003.

## Rastreabilidade

- RF-001–RF-006: T003–T010; RF-007–RF-012: T011–T016; RF-013–RF-020: T017–T022; RF-021–RF-026: T023–T026.
- RNF-001–RNF-008 e CS-001–CS-008: T005–T026, cobrindo concorrência, cancelamento, integridade atômica, limites, logs e recuperação.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F004. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- As tarefas de engenharia T001–T026 foram concluídas e validadas. O marco F005 foi atingido com 33/33 páginas PDM reais no perfil temporário QA; `B003-REAL-SOURCE` continua para fontes, itens e escopos além da autorização NDL.
