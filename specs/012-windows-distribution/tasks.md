# Tarefas de Implementação: F012 — Distribuição Windows do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [research.md], [data-model.md], contratos e checklists de release.

## Dependências

- Features anteriores: F001–F011. Empacotamento só começa após baseline de aplicação e dependências licenciadas.
- Gates sem decisão presumida: baseline de implementação ainda não existente; matriz de arquiteturas Windows (x64/ARM64/x86) precisa ser definida antes de target/release; Inno Setup é opcional e sujeito a licença.
- Reutilizar paths de usuário F001; atualização/desinstalação nunca remove biblioteca sem consentimento explícito. Não empacotar KCC ou browser sem validação de licença/requisitos.

## Fase 1 — Setup

- [ ] T001 [P] Criar inventário de runtime/dependências/licenças e versões fixadas a partir do lock real em `packaging/third-party-notices/`; sem lock atual, registrar gate de baseline, sem inventar versões.
- [ ] T002 [P] Definir fluxo genérico de build PyInstaller em `packaging/` sem selecionar arquitetura ou embutir dependências, mantendo targets específicos bloqueados até a matriz ser aprovada.
- [ ] T003 Registrar a decisão humana da matriz de arquiteturas na release checklist antes de adicionar targets específicos; manter build bloqueado enquanto faltar decisão.; arquivos/componentes: `specs/012-windows-distribution/checklists/release.md`

## Fase 2 — Foundational

- [ ] T004 Criar testes de empacotamento/manifesto de arquivos, hashes e metadados em `tests/packaging/test_release_manifest.py`.
- [ ] T005 Implementar metadados, versionamento e manifesto de artefatos conforme contratos de `specs/012-windows-distribution/contracts/`.
- [ ] T006 Criar teste de que caminhos de dados apontam para local de usuário fora da instalação em `tests/packaging/test_user_data_location.py`.
- [ ] T007 Integrar configuração de paths do F001 ao pacote isolado sem mover banco nem biblioteca para diretório instalável.; arquivos/componentes: `src/manga_to_kindle/infrastructure/paths.py; packaging/pyinstaller/`

## Fase 3 — Histórias de usuário

### US1 — Instalar e abrir em Windows limpo (P1)

**Objetivo**: Como pessoa usuária do Windows, quero receber uma distribuição do Manga to Kindle que funcione sem instalar Python ou ferramentas de desenvolvimento, para iniciar o aplicativo com seus dados isolados da pasta dos executáveis.

**Teste independente**: Em máquinas virtuais limpas de Windows 10 e 11 sem Python, `uv`, Qt ou ambiente de desenvolvimento, instalar/extrair o artefato e abrir o aplicativo; verificar versão, ícone, inicialização e criação de dados na raiz local definida por F001, fora da pasta de instalação.

- [ ] T008 [US1] Criar checklist/teste automatizável de checkout limpo, dependências e build PyInstaller em `tests/packaging/test_clean_build_inputs.py`.
- [ ] T009 [US1] Criar configuração de build, assets/ícone e metadados em `packaging/pyinstaller/` após resolução do gate de arquitetura.
- [ ] T010 [US1] Criar smoke test e evidência de abertura em VM Windows limpa compatível com a matriz aprovada; marcar como pendente até execução real.; arquivos/componentes: `tests/packaging/test_clean_build_inputs.py; specs/012-windows-distribution/checklists/release.md`

### US2 — Atualizar sem perder biblioteca/preferências (P1)

**Objetivo**: Como pessoa usuária, quero substituir uma versão anterior por uma nova, para receber correções sem perder mangás, capítulos, imagens, histórico, perfis ou preferências.

**Teste independente**: Instalar uma versão anterior com banco e arquivos de fixture, fechar o aplicativo, atualizar usando o pacote novo e comparar IDs, relações, checksums, caminhos e preferências antes/depois; simular falha na migração e verificar recuperação.

- [ ] T011 [US2] Criar teste de lifecycle de atualização que preserve diretório do usuário e migrações locais em `tests/packaging/test_update_preserves_data.py`.
- [ ] T012 [US2] Implementar mecanismo/build de atualização compatível com instalação proposta, validando backup/migração sem sobrescrever dados.; arquivos/componentes: `packaging/installer/; tests/packaging/test_update_preserves_data.py`
- [ ] T013 [US2] Testar upgrade da versão anterior e falha/rollback sem apagar banco ou exports em `tests/packaging/test_update_recovery.py`.

### US3 — Desinstalar sem apagar dados por padrão (P1)

**Objetivo**: Como pessoa usuária, quero remover os executáveis sem perder minha biblioteca, para poder reinstalar, atualizar ou encerrar o uso preservando meus dados.

**Teste independente**: Remover o aplicativo instalado com fixtures conhecidas, confirmar que a raiz de dados permanece intacta e que uma remoção de dados opcional exige confirmação separada e lista clara do escopo.

- [ ] T014 [US3] Criar teste/checklist de remoção do app e preservação de dados por padrão em `tests/packaging/test_uninstall_preserves_data.py`.
- [ ] T015 [US3] Implementar lifecycle do instalador que distingue binários de dados do usuário e exige consentimento explícito para remoção de biblioteca.; arquivos/componentes: `packaging/installer/; tests/packaging/test_uninstall_preserves_data.py`
- [ ] T016 [US3] Verificar atualização/desinstalação em instalação limpa e documentar resultado não executado como pendente.; arquivos/componentes: `tests/packaging/test_update_recovery.py; specs/012-windows-distribution/checklists/release.md`

### US4 — Publicar release rastreável e licenciada (P2)

**Objetivo**: Como pessoa mantenedora, quero reconstruir e verificar o pacote, identificar suas versões e entregar avisos de licenças, para publicar uma release auditável e legalmente revisada.

**Teste independente**: Gerar o pacote a partir de checkout limpo, versão e dependências travadas; repetir a construção, conferir manifesto de componentes/hash, metadados e arquivo de avisos; bloquear publicação se houver dependência sem decisão de licença.

- [ ] T017 [US4] Criar testes de completude de notices e bloqueio para licença desconhecida em `tests/packaging/test_dependency_licenses.py`.
- [ ] T018 [US4] Gerar inventário de terceiros, avisos e atestação/hash de artefatos usando schemas de contrato; resolver gate Inno Setup antes do seu uso.; arquivos/componentes: `packaging/third-party-notices/; specs/012-windows-distribution/contracts/artifact-attestation.schema.json; specs/012-windows-distribution/contracts/release-manifest.schema.json`
- [ ] T019 [US4] Criar checklist de release por arquitetura/aprovação, assinatura se prevista, testes manuais e pendências em `specs/012-windows-distribution/checklists/release.md`.
- [ ] T020 [US4] Confirmar que KCC/browser opcionais não são embutidos e documentar suas dependências/licenças sem presumir disponibilidade.; arquivos/componentes: `README.md; specs/012-windows-distribution/research.md`

## Fase 4 — Integração

- [ ] T021 Integrar build a partir do baseline travado das F001–F011 em `tests/packaging/test_release_from_clean_checkout.py`.
- [ ] T022 Testar instalação, migração, atualização e desinstalação sequenciais em Windows limpo e anexar evidências datadas ao checklist.; arquivos/componentes: `tests/packaging/test_update_recovery.py; tests/packaging/test_uninstall_preserves_data.py; specs/012-windows-distribution/checklists/release.md`

## Fase 5 — Polish e validação

- [ ] T023 Executar validação dos manifests e hashes sem publicar artefato até que todos os gates de arquitetura/licença estejam resolvidos.; arquivos/componentes: `tests/packaging/test_release_manifest.py; specs/012-windows-distribution/checklists/release.md`
- [ ] T024 Revisar README para instruções de instalação, localização dos dados, atualização e desinstalação com preservação padrão.; arquivos/componentes: `README.md`
- [ ] T025 Marcar no checklist como pendente qualquer teste de Windows limpo, Kindle físico ou rota externa não executado; não relatar como aprovado.; arquivos/componentes: `specs/012-windows-distribution/checklists/release.md`

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
- Nenhuma tarefa aparece concluída nesta etapa.
