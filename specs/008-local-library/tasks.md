# Tarefas de Implementação: F008 — Biblioteca Local do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/library.md] e constituição.

## Dependências

- Features anteriores: F001–F007. Usar o único engine/runner Alembic de F001 e consolidar F005–F007 sem duplicar suas migrações ou repositórios de responsabilidade.
- F009–F011 dependem dos registros e consultas estáveis desta feature.

## Fase 1 — Setup

- [x] T001 [P] Confirmar SQLAlchemy 2, Alembic e versões no lock existente; não substituir nem criar segundo engine.; SQLAlchemy `2.1.9` e Alembic `1.20.1` confirmados no runtime/lock, sem alteração de dependência.
- [x] T002 [P] Criar conjunto sintético de dados de teste para manga, capítulos, jobs, páginas e exports em `tests/fixtures/library/`; nunca é carregado automaticamente no perfil do aplicativo.

## Fase 2 — Foundational

- [x] T003 Criar testes de integridade referencial e migrações sobre esquema criado por F001 em `tests/integration/test_library_schema.py`; FK inválida é rejeitada e a migração preserva IDs.
- [x] T004 Implementar revisão Alembic `0006_library`, índices/modelos e repository SQLAlchemy em `src/manga_to_kindle/infrastructure/persistence/library_repository.py`.
- [x] T005 Criar testes de mapeamento e invariantes do catálogo persistido em `tests/unit/infrastructure/test_library_mapping.py`.
- [x] T006 Implementar casos de uso e repositório de consultas/favoritos/histórico em `src/manga_to_kindle/application/library/` e `src/manga_to_kindle/infrastructure/persistence/library_repository.py`, sem duplicar serviços originadores.

## Fase 3 — Histórias de usuário

### US1 — Encontrar conteúdo na biblioteca local (P1)

**Objetivo**: Como pessoa usuária, quero pesquisar, filtrar e ordenar meus mangás e capítulos, para localizar rapidamente o conteúdo disponível no dispositivo.

**Teste independente**: Cadastrar fixtures de mangás/capítulos com metadados variados, favoritos e estados de arquivo; pesquisar termos com diferenças de caixa/acentos, aplicar filtros e conferir ordenação estável.

- [x] T007 [US1] Criar testes de busca case/acento, filtros, favoritos e ordenação estável em `tests/integration/test_library_search.py`; inclui teste de escala de 10.000 mangás/100.000 capítulos.
- [x] T008 [US1] Implementar casos de uso de busca/filtro/favoritos/ordenação em `src/manga_to_kindle/application/library/queries.py`.
- [x] T009 [US1] Criar testes de estados vazio, resultados, filtros e teclado em `tests/ui/test_library_view.py`.
- [x] T010 [US1] Integrar listagem, pesquisa e filtros na tela Biblioteca usando consultas fora da UI thread em `src/manga_to_kindle/presentation/qt/views/library_view.py`.

### US2 — Consultar disponibilidade, downloads e histórico (P1)

**Objetivo**: Como pessoa usuária, quero ver quais capítulos já foram baixados, quais arquivos existem e como terminaram operações recentes, para saber o que está pronto sem repetir trabalho.

**Teste independente**: Criar trabalhos concluídos, parciais, cancelados e interrompidos, exports e arquivos faltantes; reiniciar o aplicativo e verificar classificações, progresso e histórico.

- [x] T011 [US2] Criar testes de estados de jobs e caminhos ausentes em `tests/integration/test_library_availability.py` e `tests/integration/test_library_search.py`.
- [x] T012 [US2] Implementar disponibilidade derivada dos registros/pastas F005–F007 em `src/manga_to_kindle/application/library/availability.py`; caminhos e hashes são conferidos em worker.
- [x] T013 [US2] Criar testes de reinício e histórico de exportação/importação em `tests/integration/test_library_history.py` e `tests/integration/test_library_restart.py`; snapshots preservam identidade.
- [x] T014 [US2] Integrar histórico e indicadores à Biblioteca sem duplicar filas/downloads da tela correspondente em `src/manga_to_kindle/presentation/qt/views/library_view.py`.

### US3 — Remover com escopo explícito (P2)

**Objetivo**: Como pessoa usuária, quero escolher exatamente quais registros e arquivos excluir e revisar o impacto antes de confirmar, para evitar perder conteúdo por uma ação ambígua.

**Teste independente**: Preparar um mangá com capítulos, jobs, imagens e export; cancelar a confirmação e verificar que tudo permanece. Depois confirmar somente registros e, em outro caso, registros mais arquivos específicos; conferir escopo, hashes e recuperação de falha.

- [x] T015 [US3] Criar testes de cancelamento, registro-only, paths selecionados, origem externa, arquivo alterado e recuperação em `tests/security/test_library_delete_scope.py`.
- [x] T016 [US3] Implementar plano persistido e prévia explícita no repository; verificar raiz, symlink, compartilhamento e checksum antes de remover arquivo.
- [x] T017 [US3] Testar referências preservadas, caminhos compartilhados e recuperação de plano interrompido em `tests/security/test_library_delete_scope.py` e `tests/integration/test_library_history.py`.
- [x] T018 [US3] Integrar diálogos de confirmação, cancelamento e gestão posterior de arquivos sem vínculo à UI; cancelamento não modifica registros nem arquivos.

## Fase 4 — Integração

- [x] T019 Integrar metadados/importação F006, exports F007 e registros persistidos de download F005 nas projeções/histórico; validar importação/exportação end-to-end. A ausência de fonte autorizada mantém downloads reais bloqueados na F005.
- [x] T020 Testar migração, arquivo local, favoritos e busca após reabertura do SQLite em `tests/integration/test_library_restart.py`.

## Fase 5 — Polish e validação

- [x] T021 Documentar busca, estados de disponibilidade e semântica exata das opções de exclusão em `specs/008-local-library/quickstart.md`.
- [x] T022 Executar testes focados, suíte completa, smoke de startup, Ruff e MyPy; registrar evidência no quickstart e checkpoint.

## Dependências e estratégia de execução

- Requer `F001:T017` a `F007:T024`; migrações novas são acrescentadas ao runner central. F009/F010/F011 aguardam `F008:T020`.
- Índices e repositórios precedem consultas; não reproduzir lógica dos módulos de downloads, imagens ou exports.
- US1–US3 implementadas; a interface exige prévia e confirmação explícita antes de remover registros/arquivos. Somente arquivos gerenciados e exports registrados por caminho/hash podem ser removidos.

## Rastreabilidade

- RF-001–RF-012: T003–T010; RF-013–RF-023: T011–T014/T019–T020; RF-024–RF-033: T015–T022.
- RNF-001–RNF-008 e CS-001–CS-010: T003–T022, incluindo migração, reinício, arquivos externos ausentes e exclusão explícita.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F007. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Tarefas marcadas concluídas têm artefato e validação registrados acima e no checkpoint local.
