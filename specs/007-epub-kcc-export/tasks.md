# Tarefas de Implementação: F007 — Exportação EPUB e KCC do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/export.md], [research.md] e constituição.

## Dependências

- Features anteriores: F001–F006 (contratos, UI, pages, provider, biblioteca local e pipeline de imagens).
- Reutilizar páginas derivadas e metadados existentes; exportar localmente e nunca transferir sem consentimento separado em F009.
- Gates obrigatórios: resolver licença/uso de EbookLib (AGPL), layout fixo/Send to Kindle sem alegações não testadas, inicialização KCC sem rede e capacidades/argumentos reais do KCC instalado. Não empacotar KCC.

## Fase 1 — Setup

- [ ] T001 [P] Revisar licença, versão e API EbookLib e registrar decisão em `specs/007-epub-kcc-export/research.md` antes de incluir dependência.
- [ ] T002 [P] Criar fixtures de páginas, capas e metadados sob `tests/fixtures/exports/`.

## Fase 2 — Foundational

- [ ] T003 Criar testes de plano de exportação, ordem, metadados ausentes e direção em `tests/unit/application/test_export_plan.py`.
- [ ] T004 Implementar modelo/validação de Export e plano imutável de leitura em `src/manga_to_kindle/domain/exports.py` e `application/exports/plan.py`.
- [ ] T005 Criar testes de writer atômico, nomes, limite e limpeza em `tests/integration/test_export_staging.py`.
- [ ] T006 Implementar staging de saída e promoção atômica em `src/manga_to_kindle/infrastructure/exports/output_store.py`.

## Fase 3 — Histórias de usuário

### US1 — Exportar EPUB organizado (P1)

**Objetivo**: Como pessoa usuária, quero exportar capítulos ou volumes com capa, metadados, sumário e direção de leitura configurável, para ler uma cópia local das páginas em um leitor compatível.

**Teste independente**: Exportar uma fixture com vários capítulos, páginas, capa e metadados; verificar o pacote EPUB, o sumário, a ordem do spine, a direção, os arquivos e a ausência de qualquer transferência.

- [ ] T007 [US1] Criar testes de estrutura EPUB, capa, metadata, TOC, spine, RTL/LTR e ordem de páginas em `tests/integration/test_native_epub.py`.
- [ ] T008 [US1] Implementar EPUB nativo por adaptador validado de EbookLib somente após gate de licença; caso bloqueado, manter dependência não incorporada e registrar impedimento em `research.md`.; arquivos/componentes: `src/manga_to_kindle/infrastructure/exports/epub_writer.py; specs/007-epub-kcc-export/research.md`
- [ ] T009 [US1] Criar testes de divisão por capítulo/volume/tamanho sem omissão ou reordenação em `tests/unit/application/test_export_partitioning.py`.
- [ ] T010 [US1] Implementar estratégia de agrupamento/divisão configurável em `src/manga_to_kindle/application/exports/partition.py`.
- [ ] T011 [US1] Criar testes de validação estrutural e conteúdo corrompido em `tests/security/test_epub_validation.py`.
- [ ] T012 [US1] Validar EPUB resultante, metadados obrigatórios e referências internas antes de promoção atômica.; arquivos/componentes: `src/manga_to_kindle/infrastructure/exports/epub_validator.py; tests/security/test_epub_validation.py`

### US2 — Escolher divisão e formato opcional (P2)

**Objetivo**: Como pessoa usuária, quero dividir resultados acima de um tamanho escolhido e opcionalmente gerar CBZ, para controlar o tamanho dos arquivos mantendo páginas e capítulos completos.

**Teste independente**: Exportar uma fixture acima do limite definido e conferir partes numeradas; exportar a mesma seleção em CBZ e comparar identidade e ordem das imagens.

- [ ] T013 [US2] Criar testes de CBZ opcional comparando identidade/ordem das imagens em `tests/integration/test_cbz_export.py`.
- [ ] T014 [US2] Implementar CBZ apenas conforme escopo da spec, sem reprocessar originais e preservando sequência em `infrastructure/exports/cbz_writer.py`.
- [ ] T015 [US2] Criar testes de validação de limites e opções da UI em `tests/ui/test_export_options.py`.
- [ ] T016 [US2] Integrar seleção de saída, agrupamento, limite e formato opcional à tela Conversão; deixar ação de envio fora do fluxo.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/export_view.py`

### US3 — Usar KCC compatível ou fallback nativo (P2)

**Objetivo**: Como pessoa usuária, quero usar uma instalação compatível do KCC ou escolher o EPUB nativo, para obter a saída que funciona no meu fluxo sem depender de um conversor indisponível.

**Teste independente**: Simular binários KCC ausente, compatível, com argumentos diferentes, sem opção necessária, com timeout e com saída inválida; conferir o fallback nativo, isolamento do subprocesso, cancelamento e relatório. A etapa final de aceitação compara a saída em um Kindle físico e registra o modelo e a rota testados.

- [ ] T017 [US3] Criar testes do adaptador com binário ausente, versão/help real capturado, timeout, cancelamento e saída inválida em `tests/unit/infrastructure/test_kcc_adapter.py`.
- [ ] T018 [US3] Implementar detecção KCC e argumentos exclusivamente verificados na versão instalada, `subprocess` sem shell, timeout/cancelamento e logs redigidos em `infrastructure/exports/kcc_adapter.py`.
- [ ] T019 [US3] Criar teste de integração que confirme fallback EPUB quando KCC não está instalado e nenhuma chamada de rede durante a inicialização em `tests/integration/test_export_fallback.py`.
- [ ] T020 [US3] Documentar limitações de layout fixo/Send to Kindle e só oferecer alternativa USB/AZW3 quando a capacidade for comprovada pela versão real.; arquivos/componentes: `README.md; specs/007-epub-kcc-export/quickstart.md`

## Fase 4 — Integração

- [ ] T021 Integrar pages de F006, Export de F001 e persistência no runner F001/F008 em `tests/integration/test_export_library_flow.py`.
- [ ] T022 Validar que exportação não envia nem transfere conteúdo e não altera arquivos originais em `tests/security/test_export_no_send.py`.

## Fase 5 — Polish e validação

- [ ] T023 Documentar licenças, dependências opcionais, compatibilidade conhecida e fluxo manual USB em README/quickstart.; arquivos/componentes: `README.md; specs/007-epub-kcc-export/quickstart.md`
- [ ] T024 Executar validação EPUB automatizada e registrar a etapa de teste em Kindle físico como pendente até execução manual documentada.; arquivos/componentes: `tests/integration/test_native_epub.py; specs/007-epub-kcc-export/quickstart.md`

## Dependências e estratégia de execução

- Requer `F001:T017` a `F006:T024`; não criar pipeline de imagem, saída temporária nem registry alternativos. US1 nativo pode avançar independentemente de KCC, sujeito à licença EbookLib.
- T001, T003 e T005 antecedem dependências/implementações; todas as opções KCC devem derivar de evidência da versão real.
- MVP: EPUB não transferido com estrutura validada. Critérios dependentes de licença ou dispositivo permanecem como gates.

## Rastreabilidade

- RF-001–RF-012: T003–T012; RF-013–RF-022: T013–T016; RF-023–RF-032: T017–T024.
- RNF-001–RNF-007 e CS-001–CS-009: T001–T024, com gates explícitos para licença, CLI, layout e validação física.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F006. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
