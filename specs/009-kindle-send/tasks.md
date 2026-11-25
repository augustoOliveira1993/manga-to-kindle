# Tarefas de Implementação: F009 — Envio ao Kindle do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/transfer.md], [data-model.md] e constituição.

## Dependências

- Features anteriores: F001, F002, F007 e F008 (paths/segredos, UI, exports locais e histórico da biblioteca).
- Fluxo padrão abre pasta ou Send to Kindle para ação manual. SMTP é opcional e exige destinatário autorizado e confirmação explícita por envio.
- Não automatizar login Amazon, presumir API pública, guardar credenciais em texto/logs ou confundir aceito pelo servidor com entregue.

## Fase 1 — Setup

- [ ] T001 [P] Confirmar API e disponibilidade do cofre Windows por dependência/plataforma antes de registrar adaptador em `pyproject.toml`/lock.
- [ ] T002 [P] Criar fixtures de exports e resultados SMTP simulados em `tests/fixtures/transfers/`.

## Fase 2 — Foundational

- [ ] T003 Criar testes de estado de transferência e distinção entre iniciado, aceito, falhou e não confirmado como entregue em `tests/unit/domain/test_transfer.py`.
- [ ] T004 Implementar entidade/enum de Transfer e invariantes em `src/manga_to_kindle/domain/transfers.py`.
- [ ] T005 Criar testes de persistência/histórico com migração central F001 em `tests/integration/test_transfer_repository.py`.
- [ ] T006 Implementar repository e revisão Alembic de histórico no runner único em `infrastructure/persistence/transfers/`.

## Fase 3 — Histórias de usuário

### US1 — Abrir fluxo manual do Send to Kindle (P1)

**Objetivo**: Como pessoa usuária, quero abrir a pasta que contém minha exportação e a página oficial Send to Kindle, para escolher e enviar manualmente um arquivo que revisei.

**Teste independente**: Com uma exportação EPUB válida e um lançador de sistema simulado, acionar a opção de envio manual e verificar a abertura da pasta correta e da página oficial, sem requisição de upload nem leitura automatizada da página.

- [ ] T007 [US1] Criar testes de abertura de diretório e URL oficial sem envio do app em `tests/unit/application/test_manual_transfer.py`.
- [ ] T008 [US1] Implementar ações para abrir export e Send to Kindle oficial por integração Windows validada em `src/manga_to_kindle/application/transfers/open_manual_flow.py`.
- [ ] T009 [US1] Criar testes da UI para export selecionado, diretório inexistente e cancelamento em `tests/ui/test_manual_send_view.py`.
- [ ] T010 [US1] Integrar fluxo manual à tela de exportações sem disparar SMTP nem enviar conteúdo automaticamente.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/manual_send_view.py`

### US2 — Configurar SMTP opcional (P2)

**Objetivo**: Como pessoa usuária que prefere e-mail, quero cadastrar meu servidor SMTP, remetente e endereço Kindle, para enviar um arquivo exportado sem expor minha senha à aplicação ou a seus logs.

**Teste independente**: Usar um cofre de credenciais falso e um servidor SMTP simulado para validar gravação e recuperação da configuração, TLS, autenticação, destinatário e falhas sem contatar serviços públicos.

- [ ] T011 [US2] Criar testes de validação SMTP, remetente/destinatário permitido e cofre fake em `tests/unit/application/test_smtp_settings.py`.
- [ ] T012 [US2] Implementar configuração sem segredo em SQLite/config e adaptador de credenciais para cofre do sistema em `infrastructure/security/credential_vault.py`.
- [ ] T013 [US2] Criar testes de interface para configuração inválida e credencial ausente em `tests/ui/test_smtp_settings_view.py`.
- [ ] T014 [US2] Implementar formulário PT-BR de SMTP e persistir somente referência segura ao segredo.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/smtp_settings_view.py; src/manga_to_kindle/infrastructure/security/credential_vault.py`

### US3 — Autorizar cada envio e entender resultado (P2)

**Objetivo**: Como pessoa usuária, quero revisar arquivo, destinatário e servidor antes de cada envio SMTP e saber se o servidor aceitou a mensagem, para autorizar cada transferência e não confundir aceitação com entrega.

**Teste independente**: Com servidor simulado, tentar enviar sem confirmação, confirmar um EPUB, testar respostas de aceitação e rejeição e desconexão após os dados da mensagem; verificar que somente os resultados comprováveis aparecem no histórico.

- [ ] T015 [US3] Criar testes com SMTP simulado para confirmação cancelada, aceite, rejeição, timeout e rate limit em `tests/integration/test_smtp_send.py`.
- [ ] T016 [US3] Implementar envio opt-in em worker, confirmação explícita por tentativa, timeout/limites e remoção de segredos dos logs em `src/manga_to_kindle/application/transfers/smtp_send.py`.
- [ ] T017 [US3] Criar testes da exibição que nunca rotule aceite SMTP como entrega no Kindle em `tests/ui/test_transfer_result.py`.
- [ ] T018 [US3] Integrar estado e resultado observável à UI; manter botão de confirmação final antes de cada envio.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/transfer_result_view.py`

### US4 — Consultar histórico local (P3)

**Objetivo**: Como pessoa usuária, quero consultar o resultado e o horário das tentativas anteriores, para distinguir exportações locais de mensagens aceitas ou falhas de envio.

**Teste independente**: Registrar tentativas simuladas aceitas, rejeitadas, canceladas e ambíguas; reiniciar o aplicativo e conferir estado, vínculo com a exportação e ausência de reenvio automático.

- [ ] T019 [US4] Criar testes de histórico após reinício e retenção de metadados mínimos em `tests/integration/test_transfer_history.py`.
- [ ] T020 [US4] Implementar consulta e tela de histórico sem conteúdo sensível em `application/transfers/history.py` e view correspondente.

## Fase 4 — Integração

- [ ] T021 Integrar Export de F007, path/biblioteca de F008 e registro de transferência F009 em `tests/integration/test_export_to_transfer_flow.py`.
- [ ] T022 Testar ausência de envio em background, sem login web automatizado e sem credencial em logs em `tests/security/test_transfer_no_automation.py`.

## Fase 5 — Polish e validação

- [ ] T023 Documentar distinção entre ação manual, aceitação SMTP e entrega; descrever configuração do cofre no README/quickstart.; arquivos/componentes: `README.md; specs/009-kindle-send/quickstart.md`
- [ ] T024 Executar testes com SMTP local simulado e registrar que entrega real não é afirmada nem verificada pelo aplicativo.; arquivos/componentes: `tests/integration/test_smtp_send.py; tests/security/test_transfer_no_automation.py`

## Dependências e estratégia de execução

- Requer `F001:T017`, `F002:T018`, `F007:T024` e `F008:T020`. O fluxo manual deve ser entregue mesmo se SMTP/cofre não estiverem disponíveis.
- SMTP só é desbloqueado após validação de cofre do sistema; testes sempre usam servidor local simulado.
- MVP: US1; envio SMTP não é default nem parte da aceitação do fluxo manual.

## Rastreabilidade

- RF-001–RF-008: T003–T010; RF-009–RF-017: T011–T014; RF-018–RF-027: T015–T018/T022; RF-028–RF-033: T019–T024.
- RNF-001–RNF-007 e CS-001–CS-009: T005–T024, incluindo cofre, confirmação, privacidade, logs e status correto.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001, F002, F007 e F008. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
