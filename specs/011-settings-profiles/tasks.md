# Tarefas de Implementação: F011 — Configurações e Perfis do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/settings.md], [data-model.md] e constituição.

## Dependências

- Features anteriores: F001, F002, F005, F006, F007 e F008.
- Preferências vivem em persistência local com migrações no runner de F001; valores de processamento devem alimentar F006/F007, concorrência F005 e caminhos F008 sem cópia de regras.

## Fase 1 — Setup

- [ ] T001 [P] Confirmar catálogo de defaults e validações no schema de configuração já existente em F001; não adicionar biblioteca sem justificativa.; arquivos/componentes: `src/manga_to_kindle/domain/settings.py; src/manga_to_kindle/infrastructure/config/settings.py`
- [ ] T002 [P] Preparar fixtures de configurações válidas, inválidas e antigas em `tests/fixtures/settings/`.

## Fase 2 — Foundational

- [ ] T003 Criar testes de validação/defaults para dimensão, qualidade, direção, concorrência, tema, paths e cache em `tests/unit/domain/test_settings_validation.py`.
- [ ] T004 Implementar Settings/DeviceProfile tipados com defaults Kindle Básico 8ª/10ª geração e especificação de 600×800 prevista na spec em `src/manga_to_kindle/domain/settings.py`.
- [ ] T005 Criar testes de migração/reload de preferências usando Alembic central em `tests/integration/test_settings_persistence.py`.
- [ ] T006 Implementar repository/migração compatível para preferências e perfis customizados em `infrastructure/persistence/settings/`.

## Fase 3 — Histórias de usuário

### US1 — Escolher e manter perfis (P1)

**Objetivo**: Como pessoa usuária, quero selecionar um perfil Kindle predefinido ou criar o meu, para reutilizar parâmetros coerentes de processamento e exportação.

**Teste independente**: Carregar os perfis de fábrica, selecionar Kindle Básico 8ª/10ª geração e Paperwhite 10ª geração, duplicar um perfil editável e tentar valores válidos/inválidos; conferir dimensões, direção, escala de cinza e imutabilidade dos perfis de fábrica.

- [ ] T007 [US1] Criar testes de perfis factory imutáveis, cópia customizável e dimensões inválidas em `tests/unit/application/test_device_profiles.py`.
- [ ] T008 [US1] Implementar casos de uso de listagem/criação/edição/aplicação do perfil em `src/manga_to_kindle/application/settings/device_profiles.py`.
- [ ] T009 [US1] Criar testes da lista, edição, cancelamento e proteção de perfil padrão na UI em `tests/ui/test_device_profiles_view.py`.
- [ ] T010 [US1] Integrar gerenciamento de perfis na área Configurações em PT-BR.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/device_profiles_view.py`

### US2 — Ajustar leitura e processamento (P1)

**Objetivo**: Como pessoa usuária, quero configurar direção de leitura, escala de cinza, margens, recorte e qualidade, para preparar imagens segundo a obra e o dispositivo sem alterar originais.

**Teste independente**: Salvar preferências válidas, reiniciar a aplicação e abrir uma prévia com recorte ligado/desligado; conferir persistência, perfil aplicado e preservação de bytes originais.

- [ ] T011 [US2] Criar testes de persistência da direção, tons, qualidade e recorte desligado por default em `tests/integration/test_reading_preferences.py`.
- [ ] T012 [US2] Implementar aplicação de preferências em interfaces consumidas por F006/F007, sem transformar/destruir originais.; arquivos/componentes: `src/manga_to_kindle/application/settings/device_profiles.py; src/manga_to_kindle/application/images/transform.py; src/manga_to_kindle/infrastructure/exports/epub_writer.py`
- [ ] T013 [US2] Criar testes de UI/validação dos controles e explicação das diferenças de Kindle Básico/Paperwhite conforme fontes documentadas em `tests/ui/test_reading_settings_view.py`.
- [ ] T014 [US2] Implementar formulários PT-BR para preferências de leitura, perfil e prévia.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/reading_settings_view.py`

### US3 — Configurar concorrência, pastas e cache (P2)

**Objetivo**: Como pessoa usuária, quero controlar o número de downloads simultâneos, os diretórios padrão e a política de cache, para adequar o uso de rede e disco ao meu computador.

**Teste independente**: Definir concorrência e caminhos válidos, tentar limites e pastas inválidas, aplicar limpeza simulada e verificar que somente itens de cache regeneráveis podem ser removidos.

- [ ] T015 [US3] Criar testes de limites de concorrência, paths inválidos/fora do escopo e limpeza somente de cache regenerável em `tests/security/test_resource_settings.py`.
- [ ] T016 [US3] Implementar validação e injeção de preferências para F005/F008, protegendo arquivos finais/originais.; arquivos/componentes: `src/manga_to_kindle/application/settings/device_profiles.py; src/manga_to_kindle/application/downloads/queue.py; src/manga_to_kindle/application/library/queries.py`
- [ ] T017 [US3] Criar testes de edição/reversão de configurações de recursos em `tests/ui/test_resource_settings_view.py`.
- [ ] T018 [US3] Integrar controles de pastas, concorrência e política de cache à UI.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/resource_settings_view.py`

### US4 — Restaurar padrões sem perda (P2)

**Objetivo**: Como pessoa usuária, quero restaurar os valores recomendados, para corrigir uma configuração sem apagar minha biblioteca, meus perfis personalizados ou minhas credenciais.

**Teste independente**: Modificar várias preferências e criar um perfil customizado; restaurar padrões, reiniciar e comparar preferências, biblioteca, exports, credenciais e perfil customizado.

- [ ] T019 [US4] Criar testes garantindo reset de preferências sem exclusão de library, exports, credenciais ou perfis customizados em `tests/integration/test_reset_preferences.py`.
- [ ] T020 [US4] Implementar reset transacional somente de preferências suportadas e confirmação adequada em `application/settings/reset_defaults.py`.
- [ ] T021 [US4] Criar testes de interface de confirmação/cancelamento de reset em `tests/ui/test_reset_settings_view.py`.
- [ ] T022 [US4] Integrar reset sem operações destrutivas nos dados de usuário.; arquivos/componentes: `src/manga_to_kindle/application/settings/reset_defaults.py; src/manga_to_kindle/presentation/qt/views/settings_view.py`

## Fase 4 — Integração

- [ ] T023 Integrar perfil, settings, F005, F006, F007 e consulta F008 em `tests/integration/test_settings_cross_feature.py`.
- [ ] T024 Testar carregamento e defaults após upgrade/rollback documentado pelo runner de migrações em `tests/integration/test_settings_migration_recovery.py`.

## Fase 5 — Polish e validação

- [ ] T025 Documentar defaults, dispositivos abrangidos e limites de validação em README/quickstart; atribuir fontes verificáveis às diferenças de modelos.; arquivos/componentes: `README.md; specs/011-settings-profiles/quickstart.md`
- [ ] T026 Executar testes focados de validação, migração, reset e segurança de paths; registrar evidências no quickstart.; arquivos/componentes: `tests/integration/test_settings_cross_feature.py; tests/security/test_resource_settings.py`

## Dependências e estratégia de execução

- Requer `F001:T017`, `F002:T018`, `F005:T026`, `F006:T024`, `F007:T024` e `F008:T020`.
- Os valores persistidos tornam-se fonte única; testes precedem cada integração. Se um dado de hardware não estiver documentado, apresentar apenas o que foi verificado, sem inventar diferenças.
- MVP: US1 + US2 com perfil básico; reset deve preservar conteúdo e perfis customizados.

## Rastreabilidade

- RF-001–RF-009: T003–T010; RF-010–RF-017: T011–T014; RF-018–RF-024: T015–T018; RF-025–RF-031: T019–T026.
- RNF-001–RNF-006 e CS-001–CS-009: T003–T026, cobrindo persistência, migração, valores inválidos, integração e não perda de conteúdo.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001, F002 e F005–F008. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
