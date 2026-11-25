# Checklist de Release: F012 — Distribuição Windows

**Propósito**: Registrar evidências de build, licenças e testes da release
**Criado**: 2026-11-25
**Feature**: [spec.md](../spec.md)
**Estado nesta especificação**: Todos os testes de release estão pendentes; nenhum foi executado nesta etapa documental.

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
- [ ] Licença de uso do compilador Inno Setup revisada para o modelo de distribuição; licença comercial adquirida quando exigida.
- [ ] `B007-EBOOKLIB-LICENSE` resolvido; nenhum pacote com licença pendente foi incluído.
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
