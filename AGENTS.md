# Instruções para agentes — Manga to Kindle

## Fontes de verdade

- Leia `.specify/memory/constitution.md` antes de alterar arquitetura ou comportamento.
- Cada funcionalidade tem `spec.md`, `plan.md` e `tasks.md` em `specs/NNN-*/`; preserve os requisitos e decisões aprovadas.
- Consulte `specs/task-dependencies.md` antes de iniciar uma feature; não avance por dependências bloqueadas.
- O código do produto usa identificadores e comentários em inglês. Interface e documentação voltada à pessoa usuária usam português brasileiro.

## Arquitetura e segurança

- Preserve as camadas `domain`, `application`, `infrastructure` e `presentation`; dependências apontam para dentro e são injetadas na composição.
- O domínio não importa PySide6, SQLAlchemy, HTTPX nem paths de instalação.
- Nenhum I/O de disco, banco, rede ou subprocesso potencialmente bloqueante roda na thread gráfica; use workers Qt, sinais e cancelamento quando aplicável.
- Dados ficam no perfil local do usuário. Preserve imagens originais e use gravação atômica, migrações versionadas e recuperação testável.
- Cada uso de fonte externa precisa de autorização explícita para o escopo correspondente: consulta de metadados e download são capacidades separadas. Não faça consultas reais sem autorização e limites documentados; não contorne DRM, CAPTCHA, autenticação, pagamento, bloqueios ou limites e valide redirects/destinos conforme a política central.
- Atualizações periódicas são opt-in por mangá e vivem somente enquanto o processo estiver aberto. Avisos de F010 não iniciam downloads, exports ou envios.
- Não envie arquivos ao Kindle nem a terceiros sem autorização explícita específica para cada envio.
- Logs devem ser sanitizados e não conter segredos, credenciais, URLs completas ou conteúdo de livros.
- Não invente APIs, dependências, versões ou opções CLI; verifique a documentação oficial e o ambiente travado.

## Fluxo de trabalho

- Procure arquivos e símbolos com `rg` antes de abrir arquivos; leia somente trechos necessários.
- Preserve alterações locais e faça a menor mudança coerente. Não formate ou reorganize arquivos inteiros sem necessidade.
- Use `uv` e mantenha `uv.lock` sincronizado quando dependências mudarem. Ruff, MyPy e Pytest são as ferramentas do projeto.
- Cada feature precisa de critérios verificáveis, testes e documentação. Marque uma tarefa como concluída somente quando o artefato e sua validação correspondente existirem.
- Não execute testes, lint, typecheck ou build globais automaticamente. Faça validações focadas para o escopo pedido; execute a suíte de feature quando a implementação ou a solicitação exigir.
- Não execute hooks de commit nem crie commits automaticamente. Não faça operações destrutivas no Git.
- Mantenha este arquivo e o README atualizados quando mudarem instalação, arquitetura, segurança ou fluxos operacionais.

## Build e instalação Windows

- O build nativo usa somente dependências do aplicativo e do grupo de build: `uv sync --locked --python 3.12 --no-default-groups --group build` e `uv run --locked --python 3.12 --no-default-groups --group build pyinstaller --clean --noconfirm packaging/pyinstaller/MangaToKindle.spec`.
- Antes de empacotar, gere o SBOM com `uv export --locked --format cyclonedx1.5 --no-default-groups --group build --output-file packaging/third-party-notices/dependency-inventory.cdx.json`, candidatos com `uv run --locked --python 3.12 --no-default-groups --group build python -m tools.release.license_inventory` e os hashes dos arquivos do bundle com `uv run --locked --python 3.12 --no-default-groups --group build python -m tools.release.bundle_inventory`. Esses artefatos não substituem revisão nem notices completos.
- `packaging/release/package-local-bundle.ps1` cria ZIPs locais com timestamp em `dist/local-release-draft`; esses rascunhos não são releases aprovadas enquanto matriz, licenças/notices e VMs limpas estiverem pendentes.
- Smoke tests do bundle devem definir `MANGA_TO_KINDLE_DATA_ROOT` para um caminho absoluto temporário. No Windows, alterar somente `LOCALAPPDATA` não redireciona `QStandardPaths` para fora da pasta conhecida do usuário.
