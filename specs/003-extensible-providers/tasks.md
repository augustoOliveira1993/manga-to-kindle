# Tarefas de Implementação: F003 — Provedores Extensíveis do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/provider.md](contracts/provider.md) e constituição.

## Dependências

- Features anteriores: F001 (tipos, erros, injeção de dependências e logs) e F002 (entrada/resultado na UI).
- F004 depende do registro e contrato definidos aqui; F005 só poderá usar fonte real após autorização verificável.
- Gate: manter provedor fixture apenas enquanto não houver fonte autorizada, documentação verificável e revisão de termos/licença. Não simular integração real.

## Fase 1 — Setup

- [x] T001 [P] Confirmar no `pyproject.toml` e lock apenas as dependências HTTP/parsing já justificadas no plano; sem Playwright sem necessidade autorizada.
- [x] T002 [P] Criar fixtures de provedores/URLs em `tests/fixtures/providers/` sem rede externa.

## Fase 2 — Foundational

- [x] T003 Criar testes do protocolo, capacidades, erros e registro em `tests/unit/domain/test_manga_provider.py` e `tests/unit/application/test_provider_registry.py`.
- [x] T004 Definir contrato tipado MangaProvider (`supports`, `get_manga`, `get_chapters`, `get_pages`), capacidades declaradas e erros tipados em `src/manga_to_kindle/domain/providers.py`.
- [x] T005 Criar testes de normalização, esquema, hostname, IP privado, DNS e redirecionamentos em `tests/unit/security/test_external_url_policy.py`.
- [x] T006 Implementar política central de URL/destino, validação a cada redirect e recusa de redes privadas em `src/manga_to_kindle/infrastructure/network/url_policy.py`; não realizar chamadas durante a validação.
- [x] T007 Criar testes para seleção determinística/ambiguidade do provedor em `tests/unit/application/test_provider_registry.py`.
- [x] T008 Implementar registro e seleção por `supports` com injeção explícita de dependências em `src/manga_to_kindle/application/providers/registry.py`.

## Fase 3 — Histórias de usuário

### US1 — Usar provedor de demonstração sem rede (P1)

**Objetivo**: Como pessoa usuária, quero informar uma URL reconhecida pelo provedor de demonstração e ver mangá, capítulos e páginas fictícios claramente identificados, sem confundi-los com conteúdo real.

**Teste independente**: Consultar uma URL sintética de fixture e verificar resultados determinísticos em `get_manga`, `get_chapters` e `get_pages`, sem resolução DNS ou rede.

- [x] T009 [US1] Criar testes de contrato e dados artificiais do provider de demonstração em `tests/unit/infrastructure/providers/test_fixture_provider.py`.
- [x] T010 [US1] Implementar provider de fixtures determinístico, com URLs sintéticas e rótulo de simulação, em `src/manga_to_kindle/infrastructure/providers/fixture_provider.py`.

### US2 — Rejeitar entrada inválida ou destino inseguro (prioridade não especificada na spec)

**Objetivo**: (Prioridade: P1)

**Teste independente**: Passar URLs malformadas, esquemas proibidos, fontes sem provedor, endereços privados e redirecionamentos inseguros; verificar erro tipado e nenhuma conexão ao destino rejeitado.

- [x] T011 [US2] Cobrir esquemas não HTTP(S), credenciais embutidas, hosts inválidos, loopback/privados, DNS alterado e redirect inseguro em `tests/security/test_provider_url_policy.py`.
- [x] T012 [US2] Integrar erros legíveis e redigidos à fronteira de aplicação em `src/manga_to_kindle/application/providers/resolve_provider.py`; recusar fonte não registrada sem rede.

### US3 — Adicionar provedores autorizados (P2)

**Objetivo**: (Prioridade: P2)

**Teste independente**: Registrar um provedor de teste com capacidades explícitas e verificar seleção única, ausência de seleção, seleção ambígua e bloqueio de capacidade sem evidência autorizada.

- [x] T013 [US3] Criar testes de declaração de capabilities e gate sem fonte aprovada em `tests/integration/test_provider_authorization_gate.py`.
- [x] T014 [US3] Documentar procedimento de revisão de autorização, licenças, limites e evidência para futuro provider em `specs/003-extensible-providers/research.md`; não implementar provider real sem evidência aprovada.

## Fase 4 — Integração

- [x] T015 Integrar provider de fixtures ao caso de uso F004 e ao boundary da UI F002 sem alterar a navegação em `tests/integration/test_provider_catalog_boundary.py`.
- [x] T016 Testar que erros tipados não vazam URLs com credenciais nem dados sensíveis para logs em `tests/security/test_provider_log_redaction.py`.

## Fase 5 — Polish e validação

- [x] T017 Atualizar README/quickstart para declarar funcionamento offline de fixtures e bloqueio de fontes reais.; arquivos/componentes: `README.md; specs/003-extensible-providers/quickstart.md`
- [x] T018 Executar testes focados de contratos e segurança; registrar qualquer dependência de integração autorizada ainda bloqueada.; arquivos/componentes: `tests/security/test_provider_log_redaction.py; specs/003-extensible-providers/quickstart.md`

## Dependências e estratégia de execução

- Requer `F001:T017` e `F002:T015`; F004 aguarda `F003:T015`.
- T003/T005/T007 podem ser preparados paralelamente; implementar URL policy antes do resolver. Sem provider de produção nesta etapa sem autorização verificável.
- MVP: US1 com fixture offline; US2 permanece obrigatório antes de aceitar qualquer URL externa.

## Rastreabilidade

- RF-001–RF-006: T003–T004; RF-007–RF-013: T005–T006/T011–T012; RF-014–RF-017: T007–T010; RF-018–RF-020: T013–T018.
- RNF-001–RNF-006 e CS-001–CS-007: T005–T018; critérios que exigem fonte real permanecem condicionados ao gate de autorização.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001 e F002. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
