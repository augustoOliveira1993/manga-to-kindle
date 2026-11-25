# Tarefas de Implementação: F005 — Downloads do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/downloads.md](contracts/downloads.md) e constituição.

## Dependências

- Features anteriores: F001–F004 (persistência, UI worker boundary, providers e catálogo/seleção).
- Reutilizar a política de URL F003, IDs e seleção F004, e runner de migrações F001. Fila não cria cliente nem regras de segurança paralelos.
- Gate: testes usam transporte fake. Downloads reais exigem provider/fonte autorizada e limites documentados; nunca contornar bloqueios.

## Fase 1 — Setup

- [ ] T001 [P] Confirmar cliente HTTPX/versão e política de dependências no projeto antes de fixar configuração em `pyproject.toml` e `uv.lock`.
- [ ] T002 [P] Criar fixtures binárias pequenas de imagem válida, inválida e acima dos limites em `tests/fixtures/downloads/`.

## Fase 2 — Foundational

- [ ] T003 Criar testes de estados e transições persistentes do DownloadJob em `tests/unit/domain/test_download_job.py`.
- [ ] T004 Implementar estado/entidade de job e invariantes de transição em `src/manga_to_kindle/domain/downloads.py`.
- [ ] T005 Criar testes do transporte fake e validação de política/limite em `tests/unit/infrastructure/test_download_transport.py`.
- [ ] T006 Implementar interface de transporte injetável com timeout, cabeçalhos e cancelamento cooperativo em `src/manga_to_kindle/infrastructure/downloads/transport.py`; fake é default em testes.
- [ ] T007 Criar testes para persistência idempotente e migração pelo engine Alembic existente em `tests/integration/test_download_repository.py`.
- [ ] T008 Implementar repository e revisão Alembic de jobs/páginas parciais em `src/manga_to_kindle/infrastructure/persistence/`; não criar runner próprio.

## Fase 3 — Histórias de usuário

### US1 — Enfileirar e acompanhar capítulos (P1)

**Objetivo**: Como pessoa usuária, quero iniciar o download autorizado dos capítulos selecionados e acompanhar páginas e capítulos, para saber o que está em andamento e o que foi concluído.

**Teste independente**: Selecionar capítulos em uma fixture de teste com transporte isolado, enfileirar o trabalho e conferir estados, limites de concorrência, progresso e ordem final das páginas.

- [ ] T009 [US1] Criar testes de concorrência limitada, ordem de página, deduplicação e progresso por capítulo/página em `tests/unit/application/test_download_queue.py`.
- [ ] T010 [US1] Implementar fila persistente, limite global configurável, progresso e deduplicação em `src/manga_to_kindle/application/downloads/queue.py`.
- [ ] T011 [US1] Criar testes de worker Qt, sinais tipados e responsividade/cancelamento em `tests/integration/test_download_worker.py`.
- [ ] T012 [US1] Implementar adaptador worker para fila com progresso em sinais, sem I/O na thread gráfica, em `src/manga_to_kindle/presentation/qt/workers/download_worker.py`.

### US2 — Controlar, pausar e cancelar trabalhos (P1)

**Objetivo**: Como pessoa usuária, quero pausar, retomar ou cancelar um trabalho, para controlar o uso da conexão e interromper uma seleção sem perder arquivos válidos já concluídos.

**Teste independente**: Pausar uma fila em execução, retomá-la, cancelar outra e interromper uma terceira durante o encerramento; verificar transições persistidas, arquivos temporários e páginas já finalizadas.

- [ ] T013 [US2] Criar testes de pause/resume/cancel e interrupção durante shutdown em `tests/integration/test_download_controls.py`.
- [ ] T014 [US2] Implementar comandos de controle cooperativo e persistência de estado após cada checkpoint seguro em `application/downloads/controls.py`.
- [ ] T015 [US2] Criar testes de estado e acessibilidade dos controles em `tests/ui/test_download_controls_view.py`.
- [ ] T016 [US2] Integrar pausa, retomada e cancelamento à tela Downloads, distinguindo retomada suportada de não suportada.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/downloads_view.py`

### US3 — Recuperar falhas sem arquivos inválidos (P1)

**Objetivo**: Como pessoa usuária, quero que falhas transitórias sejam tratadas com espera e que respostas inválidas sejam descartadas, para não receber arquivos truncados, corrompidos ou fora dos limites.

**Teste independente**: Usar um transporte de teste com timeouts, falhas transitórias, respostas HTTP 429/503, cabeçalho Retry-After, MIME incorreto, conteúdo excessivo, imagem corrompida e interrupção entre gravação e finalização; conferir política de retry e recuperação.

- [ ] T017 [US3] Criar testes de timeout, retry/backoff, `Retry-After`, 429/5xx, falha permanente e limites em `tests/unit/application/test_download_retry_policy.py`.
- [ ] T018 [US3] Implementar retry limitado que respeita `Retry-After` e rate limits declarados, sem contornar bloqueios, em `application/downloads/retry_policy.py`.
- [ ] T019 [US3] Criar testes de MIME, tamanho, decode, hash/duplicata e promoção atômica em `tests/security/test_download_file_validation.py` e `tests/integration/test_atomic_page_save.py`.
- [ ] T020 [US3] Implementar validação e staging em temporário, fsync quando aplicável e finalização atômica em `infrastructure/downloads/page_store.py`; arquivos inválidos não entram no catálogo.
- [ ] T021 [US3] Criar testes de recuperação após encerramento/reinício e limpeza segura de temporários em `tests/integration/test_download_recovery.py`.
- [ ] T022 [US3] Implementar reconciliação de jobs e arquivos pendentes na retomada do aplicativo em `application/downloads/recovery.py`.

## Fase 4 — Integração

- [ ] T023 Integrar seleção F004, URL policy F003, estado F001 e worker F002 através de teste com transporte fake em `tests/integration/test_download_flow.py`.
- [ ] T024 Verificar ordenação, limites, logs redigidos e nenhuma criação de job por atualizador ou remetente em `tests/security/test_download_boundaries.py`.

## Fase 5 — Polish e validação

- [ ] T025 Documentar fluxo fake/local, autorização exigida para fontes e recuperação da fila em README e quickstart.; arquivos/componentes: `README.md; specs/005-download-queue/quickstart.md`
- [ ] T026 Executar testes focados de retry, cancelamento, segurança de arquivos e reinício; reportar a fonte real como gate não resolvido se aplicável.; arquivos/componentes: `tests/integration/test_download_flow.py; tests/security/test_download_boundaries.py; specs/005-download-queue/quickstart.md`

## Dependências e estratégia de execução

- Requer `F001:T017`, `F002:T015`, `F003:T015` e `F004:T018`. T009–T012 constituem MVP de fila, sempre com transporte fake até liberação de fonte.
- A política de retry (T017–T018) deve anteceder qualquer implementação HTTP. Não executar download externo sem a evidência de autorização prevista em F003.

## Rastreabilidade

- RF-001–RF-006: T003–T010; RF-007–RF-012: T011–T016; RF-013–RF-020: T017–T022; RF-021–RF-026: T023–T026.
- RNF-001–RNF-008 e CS-001–CS-008: T005–T026, cobrindo concorrência, cancelamento, integridade atômica, limites, logs e recuperação.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F004. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
