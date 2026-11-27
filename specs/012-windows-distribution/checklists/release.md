# Checklist de Release: F012 — Distribuição Windows

**Propósito**: Registrar evidências de build, licenças e testes da release
**Criado**: 2026-11-25
**Feature**: [spec.md](../spec.md)
**Estado de release**: Aprovação e publicação seguem pendentes. A implementação local foi compilada e exercitada no host, mas isso não substitui build limpo, matriz aprovada nem VMs limpas.

## Evidência da implementação local — 2026-11-26

- Host: Windows 10 x64 (build 19045); Python 3.12.16; PyInstaller 6.22.3; saída PyInstaller `onedir`.
- Build do bundle: `uv run --locked --python 3.12 --no-default-groups --group build pyinstaller --clean --noconfirm packaging/pyinstaller/MangaToKindle.spec` — recompilado após F007. O bundle/instalador iniciou em perfil QA temporário e aplicou `0011_mobi_export_artifacts`; KCC e hooks de desenvolvimento permanecem fora do bundle.
- Pacote local: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\release\package-local-bundle.ps1` — concluído. Artefato `MangaToKindle-0.1.0-windows-x64-local-20261126-200905.zip`; SHA-256 `7bcc64183cc78ab5737e98e4bae8cb87817d0047d35a355d30c05094578a50c7` (**63.424.876 bytes**). Este é um rascunho local de validação, não uma release aprovada.
- Inventário auxiliar: o SBOM tem 24 componentes e 23 têm metadata candidata encontrada; `macholib==1.16.4` não está instalado neste host. O inventário por arquivo registra 263 caminhos e 149.835.697 bytes. As 24 revisões de licença permanecem pendentes e o inventário de arquivos não determina proveniência/licença; notices e recursos/runtime Qt ainda precisam de revisão.
- Testes automatizados locais F012: `uv run --locked --python 3.12 pytest tests/packaging -q` — **24 passed em 23,16s**. Regressão completa: `uv run --locked --python 3.12 pytest tests -q` — **363 passed em 133,91s**, com integração KCC real por `M2K_KCC_EXE`. Ruff: **All checks passed**; MyPy: **153 arquivos sem issues**. A aprovação de release permanece pendente independentemente desses testes.
- O perfil de dados do usuário foi isolado por `MANGA_TO_KINDLE_DATA_ROOT`; os testes de bundle/instalador iniciaram o executável em perfil temporário e validaram a revisão `0011_mobi_export_artifacts`. Não foi migrado perfil real. Integração KCC usa páginas sintéticas F006 e binário externo, que não está no bundle.
- Nenhum item abaixo está aprovado como critério de release por esses testes locais. Arquitetura, licenças/notices e VMs limpas permanecem pendentes.

## Build e Proveniência

- [ ] Matriz de versões do Windows e arquiteturas suportadas aprovada e declarada para a release.
- [ ] Commit de origem e versão canônica MAJOR.MINOR.PATCH registrados.
- [ ] Versões do Python, `uv.lock`, PyInstaller e ambiente Windows de build registrados.
- [ ] Build feita em Windows e a partir de checkout limpo, sem dependências locais não registradas.
- [ ] Segunda build com mesmos inputs comparada por manifesto, componentes e hashes.
- [ ] Qualquer diferença binária não determinística explicada; nenhuma reprodutibilidade bit a bit declarada sem hash idêntico.
- [ ] Ícone, metadados de produto/editor/copyright/versão conferidos no artefato Windows.
- [ ] Hashes SHA-256 dos pacotes e assinatura digital (se usada) verificados e publicados.

## Licenças e Componentes de Terceiros

- [ ] Dependências diretas e transitivas, recursos, runtimes, versões, origem e licenças inventariados.
- [ ] Textos de licença, atribuições e avisos obrigatórios incluídos na distribuição/documentação.
- [ ] Licença/exception do PyInstaller da versão selecionada revisada e registrada.
- [x] Inno Setup não foi usado; se for escolhido em outra versão do instalador, revisar a licença aplicável antes de compilar/distribuir.
- [x] `B007-EBOOKLIB-LICENSE` resolvido pela decisão F007 de usar writer da biblioteca padrão; EbookLib não está no lock nem no artefato.
- [ ] KCC e navegador padrão permanecem fora do pacote ou têm aprovação/documentação específica registrada.
- [ ] Dependências opcionais têm requisitos, versão/capacidades e instalação manual documentados.

## Instalação Limpa — Windows 10

- [ ] Teste em VM/ambiente descartável Windows 10 sem Python, `uv`, Qt ou ferramentas de desenvolvimento.
- [ ] Instalação/extrair pacote conclui sem solicitar componentes não documentados.
- [ ] Aplicativo abre, mostra ícone e versão corretos e fecha sem erro.
- [ ] Banco, configuração, logs, cache e biblioteca ficam fora da pasta de instalação.
- [ ] Funções principais abrem com KCC e browser não empacotados.
- [ ] Evidências, versão da VM, arquitetura, resultado e hashes registrados.

## Instalação Limpa — Windows 11

- [ ] Teste em VM/ambiente descartável Windows 11 sem Python, `uv`, Qt ou ferramentas de desenvolvimento.
- [ ] Instalação/extrair pacote conclui sem solicitar componentes não documentados.
- [ ] Aplicativo abre, mostra ícone e versão corretos e fecha sem erro.
- [ ] Banco, configuração, logs, cache e biblioteca ficam fora da pasta de instalação.
- [ ] Funções principais abrem com KCC e browser não empacotados.
- [ ] Evidências, versão da VM, arquitetura, resultado e hashes registrados.

## Atualização e Migração

- [ ] Upgrade testado da versão anterior suportada com banco e arquivos de fixture.
- [ ] IDs, relações, preferências, caminhos e checksums antes/depois comparados.
- [ ] Backup pré-migração e recuperação em migração interrompida/falha verificados.
- [ ] Aplicativo aberto, cancelamento, espaço insuficiente e arquivos em uso testados.
- [ ] Downgrade/incompatibilidade bloqueados com mensagem e procedimento seguro.

## Desinstalação e Dados

- [ ] Desinstalação padrão remove somente app/atalhos/entradas e preserva raiz de dados.
- [ ] Hashes de base, originais, derivados e exports comparados após desinstalação.
- [ ] Opção de remoção de dados apresenta caminho/categorias e exige confirmação extra.
- [ ] Escopo confirmado não apaga exports externos, fontes ou arquivos não selecionados.
- [ ] Cancelar remoção/desinstalação preserva todos os dados esperados.
- [ ] Reinstalação após remoção padrão reabre biblioteca preservada.

## Documentação e Aprovação

- [ ] README documenta instalação/extração, atualização, desinstalação, dados locais e dependências opcionais.
- [ ] `THIRD-PARTY-NOTICES` e changelog/release notes incluídos e revisados.
- [ ] Todos os critérios de aceitação da F012 têm evidência registrada.
- [ ] Itens reprovados foram corrigidos ou release explicitamente bloqueada; nenhum item pendente foi apresentado como aprovado.
