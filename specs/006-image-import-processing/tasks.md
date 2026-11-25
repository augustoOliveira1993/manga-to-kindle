# Tarefas de Implementação: F006 — Importação e Processamento de Imagens

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/image-processing.md](contracts/image-processing.md) e constituição.

## Dependências

- Features anteriores: F001–F005; processamento deve aceitar páginas locais/autorizadas sem depender de uma fonte remota ativa.
- Reutilizar Page/DeviceProfile e paths de F001, fila e arquivos validados de F005, perfil default Kindle Básico 10ª geração 600×800. Pillow conforme plano; originais imutáveis.
- Gate de entrada remota herdado de F003/F005; importar apenas arquivos sob controle/autorização da pessoa usuária.

## Fase 1 — Setup

- [ ] T001 [P] Confirmar versão/recursos de Pillow no lock do projeto e limites de imagem no configuration schema.; arquivos/componentes: `pyproject.toml; uv.lock; src/manga_to_kindle/infrastructure/config/settings.py`
- [ ] T002 [P] Criar fixtures JPEG/PNG/WEBP e CBZ com EXIF, transparência, páginas duplas e entradas maliciosas em `tests/fixtures/images/`.

## Fase 2 — Foundational

- [ ] T003 Criar testes de ordenação natural, filtros de extensão e validação de limites em `tests/unit/application/test_image_import_validation.py`.
- [ ] T004 Implementar scanner de diretório/CBZ com allowlist JPEG/PNG/WEBP e limites definidos (entradas, imagens, bytes e megapixels) em `src/manga_to_kindle/application/images/import_source.py`.
- [ ] T005 Criar testes de traversal, links, nomes absolutos, entradas duplicadas e decompression bomb em `tests/security/test_archive_extraction.py`.
- [ ] T006 Implementar leitura segura de CBZ sem extração insegura e rejeição atômica do lote inválido em `src/manga_to_kindle/infrastructure/images/archive_reader.py`.
- [ ] T007 Criar testes da preservação por hash e do armazenamento de originais em `tests/integration/test_original_image_store.py`.
- [ ] T008 Implementar armazenamento imutável de originais e derivados em caminhos distintos sob diretórios de usuário em `infrastructure/images/image_store.py`.

## Fase 3 — Histórias de usuário

### US1 — Importar imagens locais com segurança (P1)

**Objetivo**: Como pessoa usuária, quero importar uma pasta ou arquivo CBZ autorizado para um mangá e capítulo, para manter minhas páginas organizadas localmente.

**Teste independente**: Selecionar uma pasta e um CBZ de fixture com imagens WEBP, PNG e JPEG, revisar a prévia ordenada e importar. Comparar hashes dos originais e testar um arquivo malicioso ou acima dos limites sem criar dados parciais.

- [ ] T009 [US1] Criar testes de seleção de pasta/CBZ, prévia natural e lote abortado sem estado parcial em `tests/integration/test_import_images.py`.
- [ ] T010 [US1] Implementar caso de uso de importação, deduplicação estável e metadados Page em `src/manga_to_kindle/application/images/import_pages.py`.
- [ ] T011 [US1] Criar testes dos estados de importação e cancelamento de operação longa em `tests/ui/test_image_import_view.py`.
- [ ] T012 [US1] Implementar fluxo de seleção, prévia e progresso em worker na tela Importar/Adicionar em `presentation/qt/views/image_import_view.py`.

### US2 — Preparar páginas para perfil Kindle (P1)

**Objetivo**: Como pessoa usuária, quero visualizar páginas corrigidas e dimensionadas para o perfil Kindle Básico 10ª geração, para obter páginas legíveis em 600×800 sem esticar a imagem.

**Teste independente**: Processar fixtures com orientações EXIF diferentes, imagens coloridas, em escala de cinza e com transparência; verificar dimensões, orientação, preenchimento e proporção do derivado, e confirmar que os bytes do original não mudaram.

- [ ] T013 [US2] Criar testes para EXIF, proporção, escala de cinza, transparência e 600×800 sem distorção em `tests/unit/application/test_image_transform.py`.
- [ ] T014 [US2] Implementar pipeline Pillow para orientação, composição de transparência, escala de cinza e ajuste proporcional sem alterar originais em `src/manga_to_kindle/application/images/transform.py`.
- [ ] T015 [US2] Criar testes de cancelamento, progresso e remoção de temporários em `tests/integration/test_image_transform_worker.py`.
- [ ] T016 [US2] Executar processamento em worker cancelável com promoção atômica dos derivados em `src/manga_to_kindle/presentation/qt/workers/image_worker.py` e image store.

### US3 — Revisar recorte e páginas duplas (P2)

**Objetivo**: Como pessoa usuária, quero revisar páginas antes de aplicar recorte ou divisão de páginas duplas, para evitar remover conteúdo ou inverter a ordem de leitura.

**Teste independente**: Abrir páginas com margens uniformes, sem margens, conteúdo próximo às bordas e uma imagem panorâmica; confirmar que recorte vem desativado, que sua prévia não altera o original e que uma dupla dividida respeita a direção de leitura selecionada.

- [ ] T017 [US3] Criar testes com recorte ligado/desligado, margens, conteúdo de borda e direção RTL/LTR em `tests/unit/application/test_crop_and_spread.py`.
- [ ] T018 [US3] Implementar recorte opcional desativado por padrão e divisão configurável de página dupla, mantendo arquivo original, em `application/images/crop_and_spread.py`.
- [ ] T019 [US3] Criar testes da prévia de antes/depois e confirmação do usuário em `tests/ui/test_image_preview.py`.
- [ ] T020 [US3] Integrar prévia comparável e controles acessíveis à UI; não persistir recorte sem confirmação.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/image_import_view.py; tests/ui/test_image_preview.py`

## Fase 4 — Integração

- [ ] T021 Integrar DeviceProfile F001/F011 quando disponível e testar fallback do perfil base sem duplicar configuração em `tests/integration/test_image_profile_flow.py`.
- [ ] T022 Testar cancelamento na thread de trabalho, preservação de originais e recuperação de derivados interrompidos em `tests/integration/test_image_pipeline_recovery.py`.

## Fase 5 — Polish e validação

- [ ] T023 Documentar formatos aceitos, limites de importação, perfil 600×800 e recorte desativado por padrão no quickstart.; arquivos/componentes: `README.md; specs/006-image-import-processing/quickstart.md`
- [ ] T024 Executar testes focados de segurança CBZ, Pillow e integridade dos originais; registrar recursos/limites como valores testáveis.; arquivos/componentes: `tests/security/test_archive_extraction.py; tests/integration/test_image_pipeline_recovery.py`

## Dependências e estratégia de execução

- Requer `F001:T017` a `F005:T026`; não reimplementar filas, paths, logger ou resolução de perfil. US1 pode entregar importação local antes da resolução de fonte real.
- T004–T008 devem preceder o pipeline; em cada história, teste vem antes da implementação.
- MVP: US1 e transformação base de US2; recorte/páginas duplas ficam em US3.

## Rastreabilidade

- RF-001–RF-009: T003–T012; RF-010–RF-019: T013–T016; RF-020–RF-029: T017–T024.
- RNF-001–RNF-008 e CS-001–CS-010: T003–T024, incluindo limites de recursos, traversal, responsividade, ordenação e hash de originais.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F005. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
