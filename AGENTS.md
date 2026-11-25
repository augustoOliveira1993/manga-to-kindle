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
- Fontes externas precisam autorizar download. Não contorne DRM, CAPTCHA, autenticação, pagamento, bloqueios ou limites; valide redirects e destinos conforme a política central.
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
