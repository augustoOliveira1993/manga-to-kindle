# Tarefas de Implementação: F011 — Configurações e Perfis do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/settings.md], [data-model.md] e constituição.

## Dependências

- Features anteriores: F001, F002, F005, F006, F007 e F008.
- Preferências vivem em persistência local com migrações no runner de F001; valores de processamento devem alimentar F006/F007, concorrência F005 e caminhos F008 sem cópia de regras.

## Fase 1 — Setup

- [x] T001 [P] Confirmar catálogo de defaults e validações no schema de configuração já existente em F001; não adicionar biblioteca sem justificativa.; arquivos/componentes: `src/manga_to_kindle/domain/settings.py; src/manga_to_kindle/infrastructure/config/settings.py`
- [x] T002 [P] Preparar fixtures de configurações válidas, inválidas e antigas em `tests/fixtures/settings/`; as três fixtures são consumidas por testes automatizados.

## Fase 2 — Foundational

- [x] T003 Criar testes de validação/defaults para dimensão, qualidade, direção, concorrência, tema, paths e cache em `tests/unit/domain/test_settings_validation.py` e `tests/unit/infrastructure/test_settings.py`.
- [x] T004 Implementar Settings/DeviceProfile tipados com perfis Básico 8ª/10ª e Paperwhite 10ª, preservando 600×800 como default em `src/manga_to_kindle/domain/settings.py`.
- [x] T005 Criar testes de migração/reload de preferências usando o runner central em `tests/integration/test_settings_persistence.py` e `tests/integration/test_library_schema.py`.
- [x] T006 Implementar repository e migrações compatíveis para preferências e perfis customizados em `src/manga_to_kindle/infrastructure/persistence/settings_repository.py` e `src/manga_to_kindle/infrastructure/persistence/migrations/versions/0008_settings.py`.

## Fase 3 — Histórias de usuário

### US1 — Escolher e manter perfis (P1)

**Objetivo**: Como pessoa usuária, quero selecionar um perfil Kindle predefinido ou criar o meu, para reutilizar parâmetros coerentes de processamento e exportação.

**Teste independente**: Carregar os perfis de fábrica, selecionar Kindle Básico 8ª/10ª geração e Paperwhite 10ª geração, duplicar um perfil editável e tentar valores válidos/inválidos; conferir dimensões, direção, escala de cinza e imutabilidade dos perfis de fábrica.

- [x] T007 [US1] Criar testes de perfis internos somente leitura, cópia customizável e dimensões inválidas em `tests/unit/application/test_device_profiles.py` e `tests/unit/domain/test_settings_validation.py`.
- [x] T008 [US1] Implementar casos de uso de listagem/criação/edição/aplicação do perfil em `src/manga_to_kindle/application/settings/device_profiles.py`.
- [x] T009 [US1] Criar testes dos controles de perfil, edição, proteção contra remoção do perfil ativo e cancelamento/confirmacão de reset na UI em `tests/ui/test_settings_view.py`.
- [x] T010 [US1] Integrar gerenciamento de perfis na área Configurações em PT-BR em `src/manga_to_kindle/presentation/qt/views/settings_view.py`.

### US2 — Ajustar leitura e processamento (P1)

**Objetivo**: Como pessoa usuária, quero configurar direção de leitura, escala de cinza, margens, recorte e qualidade, para preparar imagens segundo a obra e o dispositivo sem alterar originais.

**Teste independente**: Salvar preferências válidas, reiniciar a aplicação e abrir uma prévia com recorte ligado/desligado; conferir persistência, perfil aplicado e preservação de bytes originais.

- [x] T011 [US2] Criar testes de persistência da direção, tons, qualidade e recorte desligado por default em `tests/integration/test_settings_persistence.py` e `tests/unit/infrastructure/test_settings.py`.
- [x] T012 [US2] Implementar aplicação de preferências em interfaces consumidas por F006/F007, preservando originais; validação ponta a ponta em `tests/integration/test_image_profile_flow.py`.
- [x] T013 [US2] Criar testes da seleção de perfil e dimensões apresentadas na UI em `tests/ui/test_settings_view.py`; diferenças de hardware permanecem limitadas aos fatos e fontes registrados na spec.
- [x] T014 [US2] Implementar formulários PT-BR para preferências de leitura, perfil e prévia em `src/manga_to_kindle/presentation/qt/views/settings_view.py` e `src/manga_to_kindle/presentation/qt/views/image_import_view.py`.

### US3 — Configurar concorrência, pastas e cache (P2)

**Objetivo**: Como pessoa usuária, quero controlar o número de downloads simultâneos, os diretórios padrão e a política de cache, para adequar o uso de rede e disco ao meu computador.

**Teste independente**: Definir concorrência e caminhos válidos, tentar limites e pastas inválidas, aplicar limpeza simulada e verificar que somente itens de cache regeneráveis podem ser removidos.

- [x] T015 [US3] Criar testes de limites de concorrência, paths inválidos/fora do escopo e limpeza somente de cache regenerável em `tests/security/test_resource_settings.py` e `tests/unit/domain/test_settings_validation.py`.
- [x] T016 [US3] Implementar validação e injeção de preferências para caminhos/recursos F005/F008, protegendo arquivos finais/originais, em `src/manga_to_kindle/application/settings/` e `src/manga_to_kindle/main.py`.
- [x] T017 [US3] Criar testes de edição e reversão de configurações de recursos, concorrência e perfis na UI em `tests/ui/test_settings_view.py`.
- [x] T018 [US3] Integrar controles de pastas, concorrência e política de cache à UI em `src/manga_to_kindle/presentation/qt/views/settings_view.py`.

### US4 — Restaurar padrões sem perda (P2)

**Objetivo**: Como pessoa usuária, quero restaurar os valores recomendados, para corrigir uma configuração sem apagar minha biblioteca, meus perfis personalizados ou minhas credenciais.

**Teste independente**: Modificar várias preferências e criar um perfil customizado; restaurar padrões, reiniciar e comparar preferências, biblioteca, exports, credenciais e perfil customizado.

- [x] T019 [US4] Criar testes garantindo reset de preferências sem exclusão de biblioteca, exports, referências de credenciais ou perfis customizados em `tests/integration/test_reset_preferences.py`.
- [x] T020 [US4] Implementar reset transacional somente de preferências suportadas em `src/manga_to_kindle/application/settings/preferences.py`.
- [x] T021 [US4] Criar testes de interface de confirmação/cancelamento de reset em `tests/ui/test_settings_view.py`.
- [x] T022 [US4] Integrar reset sem operações destrutivas nos dados de usuário em `src/manga_to_kindle/application/settings/preferences.py` e `src/manga_to_kindle/presentation/qt/views/settings_view.py`.

## Fase 4 — Integração

- [x] T023 Integrar perfil, settings, F005/F006/F007/F008 em `tests/integration/test_desktop_startup.py` e `tests/integration/test_image_profile_flow.py`.
- [x] T024 Testar carregamento e defaults após upgrade e a recusa de downgrade que perderia dimensões configuradas em `tests/integration/test_settings_persistence.py` e `tests/integration/test_library_schema.py`.

## Fase 5 — Polish e validação

- [x] T025 Documentar defaults, dispositivos abrangidos e limites de validação em README/quickstart, mantendo explícitos os limites das diferenças de hardware em `README.md` e `specs/011-settings-profiles/quickstart.md`.
- [x] T026 Executar testes focados de validação, migração, reset e segurança de paths e a suíte completa; registrar evidências no quickstart e checkpoint.

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
- As tarefas de implementação e validação automatizada estão concluídas. Validação visual/manual em Windows e dispositivo continua registrada como critério pendente nos quickstarts, sem bloquear a continuidade do trabalho.
