# Tarefas de Implementação: F001 — Fundação do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/domain.md](contracts/domain.md) e constituição do projeto.

## Dependências

- Features anteriores: nenhuma.
- Componentes compartilhados a estabelecer: configuração e diretórios locais, logging, SQLite/Alembic, contratos de domínio e ciclo de vida.
- Todas as features F002–F012 dependem da fundação concluída; devem reutilizar seu inicializador, logger e runner de migrações.

## Fase 1 — Setup

- [x] T001 [P] Preparar `pyproject.toml`, `uv.lock` e configurações Ruff, MyPy e Pytest com versões Python/dependências compatíveis com o plano.
- [x] T002 [P] Criar a estrutura inicial `src/manga_to_kindle/` por camadas e `tests/unit/`, `tests/integration/`.

## Fase 2 — Foundational

- [x] T003 Criar testes unitários de resolução de diretórios, configuração e defaults em `tests/unit/infrastructure/test_user_paths.py` e `test_settings.py`.
- [x] T004 Implementar configuração validada e diretórios de dados do usuário em `src/manga_to_kindle/infrastructure/config/` e `infrastructure/paths.py`, sem gravar na pasta de instalação.
- [x] T005 Criar testes de banco/migração, transação, reabertura e encerramento em `tests/integration/test_database_lifecycle.py`.
- [x] T006 Implementar engine SQLite, sessão e runner único de migrações Alembic em `src/manga_to_kindle/infrastructure/persistence/`; garantir operação idempotente na inicialização.
- [x] T007 Criar testes de contratos de domínio válidos/inválidos em `tests/unit/domain/test_entities.py`.
- [x] T008 Definir contratos tipados Manga, Chapter, Page, DownloadJob, DeviceProfile e Export em `src/manga_to_kindle/domain/`, preservando invariantes do contrato.

## Fase 3 — Histórias de usuário

### US1 — Instalar e abrir pela primeira vez (P1)

**Objetivo**: Como pessoa usuária, quero instalar e abrir o Manga to Kindle em um perfil limpo do Windows para começar com uma base local pronta e sem depender de conexão externa.

**Teste independente**: Seguir as instruções do README em um ambiente limpo do Windows e confirmar que a janela inicial aparece e que os diretórios e a base local são preparados.

- [x] T009 [US1] Criar teste de inicialização em ambiente de dados vazio e repetida em `tests/integration/test_application_startup.py`.
- [x] T010 [US1] Implementar composição de dependências e inicialização local em `src/manga_to_kindle/application/bootstrap.py` e `src/manga_to_kindle/main.py`.

### US2 — Encerrar sem perder ou corromper dados (P1)

**Objetivo**: Como pessoa usuária, quero que o aplicativo encerre de forma segura para preservar a configuração e os dados locais entre sessões.

**Teste independente**: Abrir, encerrar normalmente e reabrir o aplicativo em ciclos repetidos; confirmar que a base continua íntegra e que os dados de configuração não são substituídos por padrões.

- [x] T011 [US2] Criar testes de encerramento/reabertura e recuperação após interrupção em `tests/integration/test_safe_shutdown.py`.
- [x] T012 [US2] Implementar encerramento ordenado de sessões, transações e recursos em `src/manga_to_kindle/application/lifecycle.py`.

### US3 — Entender e recuperar uma falha (P2)

**Objetivo**: Como pessoa usuária, quero receber uma mensagem clara quando a inicialização falhar para saber se posso tentar novamente ou preciso de suporte, sem expor conteúdo dos meus livros.

**Teste independente**: Injetar falhas de inicialização e migração e verificar a mensagem em português, o registro local sanitizado e a preservação dos dados anteriores.

- [x] T013 [US3] Criar testes para logging rotativo, exceções tipadas, dados sensíveis e falhas de inicialização em `tests/unit/infrastructure/test_logging.py` e `tests/integration/test_startup_errors.py`.
- [x] T014 [US3] Implementar logging rotativo sem segredos/conteúdo de livros e mapeamento de exceções para mensagens acionáveis em `src/manga_to_kindle/infrastructure/logging.py` e `application/errors.py`.

### US4 — Evoluir o catálogo com contratos consistentes (P2)

**Objetivo**: Como pessoa que mantém o produto, quero contratos de domínio estáveis para representar mangás, capítulos, páginas, tarefas de download, perfis de dispositivo e exportações sem duplicar regras de integridade em funcionalidades futuras.

**Teste independente**: Validar cada contrato com casos válidos e inválidos, sem rede, interface de catálogo ou geração de arquivos de exportação.

- [x] T015 [US4] Criar testes de serialização/invariantes para as seis entidades em `tests/unit/domain/`.
- [x] T016 [US4] Integrar os contratos de domínio à composição sem adicionar rede real em `src/manga_to_kindle/application/bootstrap.py`.

## Fase 4 — Integração

- [x] T017 Criar teste de ponta a ponta da inicialização local, migração, falha recuperável e reabertura em `tests/integration/test_foundation_flow.py`.
- [x] T018 Documentar instalação reproduzível, dados locais, backup/recuperação e diagnóstico em `README.md`; manter `AGENTS.md` alinhado às regras consolidadas.

## Fase 5 — Polish e validação

- [x] T019 Confirmar que a fundação não faz chamadas de rede e que todo caminho de dados está fora da pasta de instalação, registrando evidência em `specs/001-app-foundation/quickstart.md`.
- [x] T020 Executar verificações focadas definidas pela constituição (Pytest, Ruff e MyPy) e registrar resultados reproduzíveis no quickstart; não ocultar falhas (`specs/001-app-foundation/quickstart.md`).

## Dependências e estratégia de execução

- T004 depende de T003; T006 de T005; T008 de T007; cada tarefa de implementação de US depende de seu teste correspondente.
- T001–T002 podem começar em paralelo; as features seguintes aguardam a conclusão da integração desta feature (`F001:T017`).
- MVP: US1, incluindo setup, infraestrutura e contratos compartilhados mínimos necessários à inicialização.

## Rastreabilidade

- RF-001–RF-004: T001–T004; RF-005–RF-006: T005–T006; RF-007–RF-009: T011–T014; RF-010: T007–T008/T015–T016; RF-011: T019; RF-012–RF-013: T018–T020.
- Critérios CS-001–CS-007 e RNF-001–RNF-005: T001–T020, com evidências de abertura, persistência, migração, logs e verificações focadas.


## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: nenhuma. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- T001–T020 concluídas na F001. A execução manual em instalação limpa de Windows 10/11 e os dez ciclos manuais de interface permanecem verificações de release pendentes, fora do conjunto automatizado desta feature.
