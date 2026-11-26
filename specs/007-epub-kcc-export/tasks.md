# Tarefas de Implementação: F007 — Exportação EPUB e KCC do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/export.md], [research.md] e constituição.

## Dependências

- Features anteriores: F001–F006 (contratos, UI, pages, provider, biblioteca local e pipeline de imagens).
- Reutilizar páginas derivadas e metadados existentes; exportar localmente e nunca transferir sem consentimento separado em F009.
- Gates obrigatórios: conformidade fixed-layout/Send to Kindle sem alegações não testadas, inicialização KCC sem rede e capacidades/argumentos reais do KCC instalado. Por decisão explícita do usuário, o writer EPUB usa biblioteca padrão e EbookLib não é dependência. Não empacotar KCC.

## Fase 1 — Setup

- [x] T001 [P] Revisar licença, versão e API EbookLib e registrar decisão em `specs/007-epub-kcc-export/research.md`. Em 25/11/2026, usuário autorizou alterar RF-010 para writer próprio com biblioteca padrão; nenhuma dependência EPUB será incluída.
- [x] T002 [P] Criar fixtures sintéticas de páginas, capa e metadados sob `tests/fixtures/exports/`.

## Fase 2 — Foundational

- [x] T003 Criar testes de plano de exportação, ordem, metadados ausentes e direção em `tests/unit/application/test_export_plan.py`.
- [x] T004 Implementar contratos/validação de Export e plano imutável em `src/manga_to_kindle/domain/exports.py` e `application/exports/plan.py`.
- [x] T005 Criar testes de staging de saída, nomes, sobrescrita confirmada e limpeza em `tests/integration/test_export_staging.py`.
- [x] T006 Implementar staging de saída e promoção atômica sem sobrescrita silenciosa em `src/manga_to_kindle/infrastructure/exports/output_store.py`.

## Fase 3 — Histórias de usuário

### US1 — Exportar EPUB organizado (P1)

**Objetivo**: Como pessoa usuária, quero exportar capítulos ou volumes com capa, metadados, sumário e direção de leitura configurável, para ler uma cópia local das páginas em um leitor compatível.

**Teste independente**: Exportar uma fixture com vários capítulos, páginas, capa e metadados; verificar o pacote EPUB, o sumário, a ordem do spine, a direção, os arquivos e a ausência de qualquer transferência.

- [x] T007 [US1] Criar testes de estrutura EPUB, capa, metadata, TOC, spine, RTL/LTR, dimensão de viewport e ordem de páginas em `tests/integration/test_native_epub.py`.
- [x] T008 [US1] Implementar writer EPUB 3 próprio com `zipfile` e `xml.etree.ElementTree`, layout fixo, metadados, capa tipográfica, sumário, direção e ordem; sem biblioteca EPUB de terceiros.; arquivos/componentes: `src/manga_to-kindle/infrastructure/exports/epub_writer.py`
- [x] T009 [US1] Criar testes de divisão por capítulo/volume/tamanho sem omissão ou reordenação em `tests/unit/application/test_export_partitioning.py`.
- [x] T010 [US1] Implementar estratégia de agrupamento/divisão configurável em `src/manga_to-kindle/application/exports/partition.py`.
- [x] T011 [US1] Criar testes de validação estrutural e conteúdo corrompido em `tests/security/test_epub_validation.py`.
- [x] T012 [US1] Validar EPUB resultante, metadados obrigatórios e referências internas antes de promoção atômica.; arquivos/componentes: `src/manga_to-kindle/infrastructure/exports/epub_validator.py; tests/security/test_epub_validation.py`

### US2 — Escolher divisão e formato opcional (P2)

**Objetivo**: Como pessoa usuária, quero dividir resultados acima de um tamanho escolhido e opcionalmente gerar CBZ, para controlar o tamanho dos arquivos mantendo páginas e capítulos completos.

**Teste independente**: Exportar uma fixture acima do limite definido e conferir partes numeradas; exportar a mesma seleção em CBZ e comparar identidade e ordem das imagens.

- [x] T013 [US2] Criar testes de CBZ opcional comparando identidade/ordem das imagens em `tests/integration/test_cbz_export.py`.
- [x] T014 [US2] Implementar CBZ apenas conforme escopo da spec, sem reprocessar originais e preservando sequência em `infrastructure/exports/cbz_writer.py`.
- [x] T015 [US2] Criar testes de validação de limites e opções da UI em `tests/ui/test_conversion_export.py`.
- [x] T016 [US2] Integrar seleção de saída, agrupamento, limite e formato opcional à tela Conversão; deixar ação de envio fora do fluxo.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/conversion_view.py`

### US3 — Usar KCC compatível ou fallback nativo (P2)

**Objetivo**: Como pessoa usuária, quero usar uma instalação compatível do KCC ou escolher o EPUB nativo, para obter a saída que funciona no meu fluxo sem depender de um conversor indisponível.

**Teste independente**: Simular binários KCC ausente, compatível, com argumentos diferentes, sem opção necessária, com timeout e com saída inválida; conferir o fallback nativo, isolamento do subprocesso, cancelamento e relatório. A etapa final de aceitação compara a saída em um Kindle físico e registra o modelo e a rota testados.

- [ ] T017 [US3] Criar testes do adaptador com binário ausente, versão/help real capturado, timeout, cancelamento e saída inválida em `tests/unit/infrastructure/test_kcc_adapter.py`. **Gate aberto**: não há binário KCC instalado cuja versão/opções e comportamento sem rede possam ser verificados; runner simulado não prova capacidade real.
- [ ] T018 [US3] Implementar detecção KCC e argumentos exclusivamente verificados na versão instalada, `subprocess` sem shell, timeout/cancelamento e logs redigidos em `infrastructure/exports/kcc_adapter.py`. **Gate aberto**: nenhum executável/capacidade KCC real foi verificado.
- [x] T019 [US3] Criar teste de integração que confirme exportação EPUB nativa sem KCC configurado e sem chamada de rede durante a inicialização em `tests/integration/test_export_fallback.py`.
- [x] T020 [US3] Documentar limitações de layout fixo/Send to Kindle e indisponibilidade de KCC/USB/AZW3 sem capacidades comprovadas.; arquivos/componentes: `README.md; specs/007-epub-kcc-export/quickstart.md`

## Fase 4 — Integração

- [x] T021 Integrar páginas de F006, histórico Export de F001 e persistência de artefatos no fluxo de worker em `tests/integration/test_export_library_flow.py`.
- [x] T022 Validar que exportação não envia nem transfere conteúdo e não altera arquivos originais em `tests/security/test_export_no_send.py`.

## Fase 5 — Polish e validação

- [x] T023 Documentar a decisão de writer stdlib, ferramenta EPUBCheck, compatibilidade conhecida e validação manual USB/Kindle em README/quickstart.; arquivos/componentes: `README.md; specs/007-epub-kcc-export/quickstart.md`
- [x] T024 Validar fixture EPUB com EPUBCheck 5.4.0 (0 erros/advertências) e registrar teste em Kindle físico como pendente até execução manual documentada.; arquivos/componentes: `tests/integration/test_native_epub.py; specs/007-epub-kcc-export/quickstart.md`

## Dependências e estratégia de execução

- Requer `F001:T017` a `F006:T024`; não criar pipeline de imagem, saída temporária nem registry alternativos. US1 nativo usa biblioteca padrão por decisão explícita do usuário; KCC continua opcional.
- T001, T003 e T005 antecedem dependências/implementações; todas as opções KCC devem derivar de evidência da versão real.
- MVP: EPUB não transferido com estrutura validada. Critérios dependentes de licença ou dispositivo permanecem como gates.

## Rastreabilidade

- RF-001–RF-012: T003–T012; RF-013–RF-022: T013–T016; RF-023–RF-032: T017–T024.
- RNF-001–RNF-007 e CS-001–CS-009: T001–T024, com gates explícitos para licença, CLI, layout e validação física.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F006. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- T017 e T018 permanecem pendentes pelo gate de capacidade real do KCC; as demais tarefas do MVP EPUB/CBZ e fluxo local estão concluídas e têm validação registrada no checkpoint.
