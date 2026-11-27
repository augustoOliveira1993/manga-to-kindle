# Tarefas de Implementação: F012 — Distribuição Windows do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [research.md], [data-model.md], contratos e checklists de release.

## Dependências

- Features anteriores: F001–F011. Empacotamento só começa após baseline de aplicação e dependências licenciadas.
- Matriz aprovada em 2026-11-27: Windows 10/11 x64 somente. O baseline e um build local existem; revisão de licenças/notices e VMs limpas dos dois sistemas seguem pendentes. Inno Setup é opcional e não foi usado.
- Reutilizar paths de usuário F001; atualização/desinstalação nunca remove biblioteca sem consentimento explícito. Não empacotar KCC ou browser sem validação de licença/requisitos.

## Fase 1 — Setup

- [x] T001 [P] Completar inventário de runtime/dependências/licenças e versões fixadas a partir do lock real em `packaging/third-party-notices/`; `bundle-component-candidates.json` mapeia 222/222 arquivos do TOC e corresponde aos caminhos físicos do bundle, sem guardar caminhos absolutos. Metadata e avisos são apenas candidatos; aprovação de licenças continua em T017/T018.
- [x] T002 [P] Definir fluxo genérico de build PyInstaller em `packaging/` sem fixar arquitetura cruzada ou incluir ferramentas de desenvolvimento, mantendo a aprovação de targets bloqueada até a matriz; o ambiente de build usa somente dependências do app e do grupo `build`.
- [ ] T003 Registrar no checklist de release a matriz humana já aprovada (Windows 10/11 x64 somente), sem declarar compatibilidade antes dos testes limpos.; arquivos/componentes: `specs/012-windows-distribution/checklists/release.md`

## Fase 2 — Foundational

- [x] T004 Criar testes dos contratos tipados de manifesto/atestação em `tests/packaging/test_release_manifest.py`; hash de pacote local também é registrado pelo empacotador.
- [x] T005 Implementar metadados, versionamento e validação tipada do manifesto/atestação conforme contratos em `tools/release/manifest.py` e `packaging/windows/version-info.txt`.
- [x] T006 Criar testes de paths locais de usuário fora da instalação em `tests/packaging/test_user_data_location.py`.
- [x] T007 Integrar `AppPaths` da F001 ao bundle isolado sem mover banco nem biblioteca para diretório instalável; smoke automatizado injeta raiz temporária absoluta via `MANGA_TO_KINDLE_DATA_ROOT`.; arquivos/componentes: `src/manga_to_kindle/infrastructure/paths.py; packaging/pyinstaller/`

## Fase 3 — Histórias de usuário

### US1 — Instalar e abrir em Windows limpo (P1)

**Objetivo**: Como pessoa usuária do Windows, quero receber uma distribuição do Manga to Kindle que funcione sem instalar Python ou ferramentas de desenvolvimento, para iniciar o aplicativo com seus dados isolados da pasta dos executáveis.

**Teste independente**: Em máquinas virtuais limpas de Windows 10 e 11 sem Python, `uv`, Qt ou ambiente de desenvolvimento, instalar/extrair o artefato e abrir o aplicativo; verificar versão, ícone, inicialização e criação de dados na raiz local definida por F001, fora da pasta de instalação.

- [x] T008 [US1] Criar e executar `tests/packaging/test_release_from_clean_checkout.py`: o teste monta um snapshot isolado dos inputs atuais, sem `.git`, `.venv`, `dist` ou `build`, sincroniza somente dependências travadas de produção/build, compila o executável e exige proveniência mapeada para todos os arquivos. Execução real em Windows 10 x64: **1 passed em 94,71s**; o snapshot não comprova commit limpo nem aprovação da matriz.
- [x] T009 [US1] Criar configuração de build, assets/ícone e metadados em `packaging/pyinstaller/`; build local nativa em Windows 10 x64 passou sem declarar essa arquitetura como matriz aprovada.
- [ ] T010 [US1] Criar smoke test e evidência de abertura em VM Windows limpa compatível com a matriz aprovada; marcar como pendente até execução real.; arquivos/componentes: `tests/packaging/test_clean_build_inputs.py; specs/012-windows-distribution/checklists/release.md`

### US2 — Atualizar sem perder biblioteca/preferências (P1)

**Objetivo**: Como pessoa usuária, quero substituir uma versão anterior por uma nova, para receber correções sem perder mangás, capítulos, imagens, histórico, perfis ou preferências.

**Teste independente**: Instalar uma versão anterior com banco e arquivos de fixture, fechar o aplicativo, atualizar usando o pacote novo e comparar IDs, relações, checksums, caminhos e preferências antes/depois; simular falha na migração e verificar recuperação.

- [x] T011 [US2] Criar teste de lifecycle de atualização que preserve a raiz do usuário em `tests/packaging/test_installer_lifecycle.py`.
- [x] T012 [US2] Implementar instalação/atualização por staging, preservar a versão anterior e manter os dados fora da pasta substituída em `packaging/installer/`; os testes usam sentinela de dados local.
- [x] T013 [US2] Testar upgrade, falha pré-publicação e falha pós-publicação com rollback da instalação, sem apagar base/sentinela local em `tests/packaging/test_installer_lifecycle.py`.

### US3 — Desinstalar sem apagar dados por padrão (P1)

**Objetivo**: Como pessoa usuária, quero remover os executáveis sem perder minha biblioteca, para poder reinstalar, atualizar ou encerrar o uso preservando meus dados.

**Teste independente**: Remover o aplicativo instalado com fixtures conhecidas, confirmar que a raiz de dados permanece intacta e que uma remoção de dados opcional exige confirmação separada e lista clara do escopo.

- [x] T014 [US3] Criar teste de remoção do app e preservação de dados por padrão em `tests/packaging/test_installer_lifecycle.py`.
- [x] T015 [US3] Implementar lifecycle do instalador separado dos dados do usuário e exigir confirmação para remover arquivos do app; a remoção não apaga a biblioteca.; arquivos/componentes: `packaging/installer/; tests/packaging/test_installer_lifecycle.py`
- [x] T016 [US3] Verificar o ZIP real em uma instalação temporária Windows 10 x64: instalação, startup/migração, upgrade pelo mesmo artefato, preservação do hash do banco durante a troca, novo startup e desinstalação preservando dados (`tests/packaging/test_installer_lifecycle.py`, incluído em **34 testes de packaging aprovados em 32,01s**). A execução local não substitui os testes em VMs Windows limpas de T022.

### US4 — Publicar release rastreável e licenciada (P2)

**Objetivo**: Como pessoa mantenedora, quero reconstruir e verificar o pacote, identificar suas versões e entregar avisos de licenças, para publicar uma release auditável e legalmente revisada.

**Teste independente**: Gerar o pacote a partir de checkout limpo, versão e dependências travadas; repetir a construção, conferir manifesto de componentes/hash, metadados e arquivo de avisos; bloquear publicação se houver dependência sem decisão de licença.

- [ ] T017 [US4] Completar testes dos notices distribuídos e bloqueio para licença desconhecida em `tests/packaging/test_dependency_licenses.py`; o validador também verifica presença, conteúdo UTF-8, tamanho e hash no ZIP real durante a atestação. Testes automatizados cobrem arquivo ausente/vazio e licença `UNKNOWN`; a distribuição ainda não contém notices completos e revisados.
- [ ] T018 [US4] Completar inventário de terceiros, avisos e atestação/hash de artefatos usando schemas de contrato. `tools/release/attestation.py` gera atestação vinculada ao hash real do artefato e mantém o resultado `pending` até todos os gates serem aprovados; os 222 arquivos do bundle agora têm proveniência candidata, mas notices revisados e manifest completo para o artefato local continuam pendentes. Resolver gate Inno Setup antes do seu uso.; arquivos/componentes: `packaging/third-party-notices/; specs/012-windows-distribution/contracts/artifact-attestation.schema.json; specs/012-windows-distribution/contracts/release-manifest.schema.json`
- [x] T019 [US4] Criar checklist de release por arquitetura/aprovação, assinatura, testes manuais e pendências em `specs/012-windows-distribution/checklists/release.md`.
- [x] T020 [US4] Confirmar que KCC/browser opcionais não são embutidos e documentar seus limites sem presumir disponibilidade.; arquivos/componentes: `README.md; specs/012-windows-distribution/research.md`

## Fase 4 — Integração

- [x] T021 Integrar e executar build a partir dos inputs travados do baseline F001–F011 em `tests/packaging/test_release_from_clean_checkout.py`; a compilação isolada terminou com executável `dist/MangaToKindle/MangaToKindle.exe` não vazio e comparou os caminhos do TOC com o inventário físico (**1 passed em 94,71s**).
- [ ] T022 Testar instalação, migração, atualização e desinstalação sequenciais em Windows limpo e anexar evidências datadas ao checklist.; arquivos/componentes: `tests/packaging/test_update_recovery.py; tests/packaging/test_uninstall_preserves_data.py; specs/012-windows-distribution/checklists/release.md`

## Fase 5 — Polish e validação

- [ ] T023 Executar validação do manifest e hash do artefato local sem publicar enquanto os gates de arquitetura/licença/VM estiverem pendentes. A ferramenta e os testes de atestação existem; a validação do pacote local aguarda um manifest completo e evidências humanas, sem publicar artefato.; arquivos/componentes: `tests/packaging/test_release_manifest.py; tests/packaging/test_release_attestation.py; specs/012-windows-distribution/checklists/release.md`
- [x] T024 Revisar README para instruções de instalação, localização dos dados, atualização e desinstalação com preservação padrão.; arquivos/componentes: `README.md`
- [x] T025 Registrar no checklist como pendente cada teste de Windows limpo, arquitetura, licença ou critério manual ainda não executado; não relatar como aprovado.; arquivos/componentes: `specs/012-windows-distribution/checklists/release.md`

## Dependências e estratégia de execução

- Requer `F001:T017` a `F011:T026`; build, instalador e publicação dependem de baseline da aplicação, matriz aprovada e decisão de licença.
- T001 e T003 devem anteceder o build específico; T008–T016 podem preparar contratos/testes, mas nenhum target é assumido antes da decisão humana.
- MVP: gerar release reproduzível apenas para arquitetura aprovada; sem instalador opcional até resolver licença do Inno Setup.

## Rastreabilidade

- RF-001–RF-008: T001–T010; RF-009–RF-016: T011–T016; RF-017–RF-023: T017–T020; RF-024–RF-030: T021–T025.
- RNF-001–RNF-007 e CS-001–CS-009: T001–T025, com gates para arquitetura, baseline, licenças e execução em Windows limpo.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F011. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Tarefas locais concluídas: T001–T002, T004–T009, T011–T016, T019–T021, T024–T025. T003/T010/T017–T018/T022–T023 permanecem abertas enquanto decisão da matriz, notices/licenças revisados, validação em VMs limpas e atestação final não tiverem evidência suficiente.
