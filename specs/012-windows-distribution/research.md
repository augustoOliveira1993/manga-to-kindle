# Pesquisa de Planejamento — F012

**Revisado em**: 2026-11-25  
**Estado do checkout**: somente documentação de features; sem código Python, pyproject.toml, uv.lock, build spec ou script Inno Setup. Não há versões de runtime instaladas pelo projeto para validar.

## Decisões

### Build Windows com PyInstaller

- **Decisão**: executar PyInstaller em Windows, usar onedir como bundle portátil-base e versionar um arquivo .spec como fonte da configuração. Inno Setup pode envolver o diretório somente após revisão de licença/modelo comercial.
- **Racional**: a documentação 6.22.3 declara suporte a Python 3.8+ e que PyInstaller não é cross-compiler. onedir é o modo padrão documentado e mantém os arquivos de runtime inspecionáveis, o que ajuda a conferir Qt plugins, DLLs, licenças e conteúdo. A spec file centraliza entradas, dados e binários; quando uma spec é passada ao CLI, a maioria das opções de linha de comando é ignorada.
- **Alternativas consideradas**: onefile não é selecionado para o primeiro bundle; adicionaria extração temporária em cada execução e dificultaria a inspeção operacional sem atender requisito exclusivo. Installer obrigatório foi rejeitado pelo gate de licença do Inno Setup.
- **CLI verificada**: a sintaxe pyinstaller <script-ou-uma-spec-file> é documentada. As opções reais relevantes incluem --onedir, --onefile, --windowed/--noconsole, --icon, --version-file, --clean, --noconfirm e --add-data. --version-file adiciona recurso de versão Windows; --icon aceita .ico no Windows. A construção recorrente usará o .spec aprovado, sem repetir flags que a documentação diz serem ignoradas. O uso de --add-data, --hidden-import, --collect-*, hooks ou DLLs só será incluído após evidência da análise e da versão fixada.
- **Referências oficiais**: [manual PyInstaller 6.22.3](https://pyinstaller.org/en/stable/), [uso e opções CLI](https://pyinstaller.org/en/stable/usage.html), [spec files](https://pyinstaller.org/en/stable/spec-files.html), [hooks](https://pyinstaller.org/en/stable/hooks.html), [licença](https://pyinstaller.org/en/latest/license.html).

### uv e lock reproduzível

- **Decisão**: o build e os checks usam projeto uv, uv.lock versionado, grupos separados para dev e build, e execução bloqueada contra alteração implícita do lock (--locked).
- **Racional**: a documentação atual do uv confirma uv sync --locked, uv run --locked, --group/--extra em projeto, e uv export --format cyclonedx1.5 para exportar dependências. --locked falha se o lock estiver ausente ou desatualizado, adequado a CI/release. O lock deve ser atualizado em mudança deliberada, não durante build.
- **Comandos confirmados para a estrutura planejada**: uv sync --locked; uv run --locked --group dev pytest; uv run --locked --group build pyinstaller packaging/pyinstaller/manga_to_kindle.spec; uv export --locked --format cyclonedx1.5.
- **Alternativas consideradas**: --frozen usa lock sem validar metadados; não é a escolha para a barreira de release. Instalar ferramentas globalmente foi rejeitado para reduzir variação entre máquinas.
- **Referências oficiais**: [locking/sync](https://docs.astral.sh/uv/concepts/projects/sync/), [CLI do uv](https://docs.astral.sh/uv/reference/cli/), [projetos uv](https://docs.astral.sh/uv/guides/projects/).

### PySide6 e trabalho fora da UI

- **Decisão**: workers QObject/QThread ficam na camada de apresentação/adaptação e reportam resultado, erro, progresso e conclusão por sinais tipados para slots Qt na thread de destino. Casos de uso não conhecem widgets.
- **Racional**: a documentação Qt for Python explica conexões queued para executar o receptor no contexto da thread do receptor; QObject e sinais/slots mantêm baixo acoplamento. Isso suporta o gate constitucional de não bloquear a thread gráfica. Cancelamento passa por token/flag cooperativo e checkpoints seguros do caso de uso, não por encerramento forçado da thread.
- **Referências oficiais**: [signals and slots](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/signals_and_slots.html), [threads and QObjects](https://doc.qt.io/qtforpython-6/overviews/qtdoc-threads-qobject.html), [thread affinity em PySide6](https://doc.qt.io/qtforpython-6.10/tutorials/basictutorial/signals_and_slots.html).

### SQLite, SQLAlchemy 2 e Alembic

- **Decisão**: SQLAlchemy 2 com mapeamento declarativo tipado (DeclarativeBase, Mapped, mapped_column) e Alembic para revisões versionadas da base F001–F008. Migração é iniciada pela aplicação após backup; setup/uninstaller apenas manipulam binários.
- **Racional**: as APIs declarativas tipadas são documentadas como padrão SQLAlchemy 2; Alembic encadeia revisões e upgrade head aplica até a revisão mais recente. Autogeração é um candidato e requer revisão humana; não se aceita migração gerada sem revisão. SQLite permanece única fonte de persistência local.
- **Alternativas consideradas**: DDL ad hoc/create_all() como substituto de migrações foi rejeitado por não preservar evolução versionada; escrita direta do instalador foi rejeitada por acoplar build à estrutura do banco.
- **Referências oficiais**: [SQLAlchemy 2 declarative mapping](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html), [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [limites de autogeração Alembic](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

### Pydantic para fronteiras JSON

- **Decisão**: usar Pydantic v2 somente na validação/serialização de contratos externos, especialmente ReleaseManifest; não usá-lo como entidade de domínio nem misturá-lo com classes ORM. O JSON Schema do contrato segue Draft 2020-12.
- **Racional**: BaseModel.model_validate_json() valida JSON e model_json_schema() produz esquema; a documentação Pydantic confirma compatibilidade do JSON Schema gerado com Draft 2020-12. Isso permite contrato executável no futuro e esquema versionável sem duplicar regra de domínio.
- **Alternativas consideradas**: dataclasses puras não validam JSON por si; usar Pydantic em toda entidade do domínio acoplaria a camada interna a uma lib de fronteira.
- **Referências oficiais**: [Pydantic models](https://pydantic.dev/docs/validation/latest/concepts/models/), [Pydantic JSON Schema](https://pydantic.dev/docs/validation/latest/concepts/json_schema/).

### Licenças, SBOM e opcionais

- **Decisão**: criar inventário de componentes diretos e transitivos a partir do lock do build/runtime e notices de terceiros; bloquear release com licença desconhecida ou gate não resolvido. KCC, browser e Playwright ficam fora. Inno Setup é decisão opcional com revisão própria. EbookLib não é dependência porque F007 usa writer da biblioteca padrão.
- **Racional**: uv export documenta CycloneDX v1.5, mas SBOM não substitui avisos e textos de licença distribuídos. PyInstaller requer execução nativa em Windows. O pacote não deve instalar opcionais em segundo plano nem fazer rede no primeiro início.
- **Referências**: [export uv/CycloneDX](https://docs.astral.sh/uv/concepts/projects/sync/), [licença PyInstaller](https://pyinstaller.org/en/latest/license.html), [F007 — EPUB/KCC](../007-epub-kcc-export/spec.md), [licenças Inno Setup](https://jrsoftware.org/inno-setup/purchase).

### Ferramentas de qualidade

- **Decisão**: Ruff, MyPy e Pytest ficam no grupo dev. Os caminhos executáveis de validação são ruff check <paths>, mypy <paths> e pytest [paths].
- **Racional**: os manuais oficiais documentam estes comandos e aceitam arquivos/diretórios como alvos. O quickstart usa caminhos planejados de src e tests, que só estarão presentes depois da implementação.
- **Referências oficiais**: [Ruff CLI](https://docs.astral.sh/ruff/linter/), [MyPy execução](https://mypy.readthedocs.io/en/stable/running_mypy.html), [Pytest invocação](https://docs.pytest.org/en/stable/how-to/usage.html).

### Matriz de Windows/arquitetura

- **Decisão**: não fechar arquitetura por inferência. O formato de manifest e a checklist recebem a lista explícita aprovada; build e VMs são instanciados por par de Windows/arquitetura. Até a decisão humana, B012-ARCH-MATRIX impede anunciar suporte e fecha a publicação.
- **Racional**: a constituição limita sistema a Windows 10/11, mas não escolhe x64/ARM64/x86; a spec deliberadamente deixou essa escolha aberta.
- **Alternativas consideradas**: fixar x64 sem resposta mudaria uma decisão já encaminhada para aprovação humana; gerar artefato para arquiteturas extras sem build e VM seria declaração sem evidência.

### Manifesto estável e hash por artefato

- **Decisão**: comparar um manifest normalizado dos insumos e componentes e registrar timestamp/hash de saída em atestação associada ao artefato. Nenhuma reprodução bit a bit será declarada sem hash idêntico.
- **Racional**: separa proveniência reprodutível de metadados por execução e atende conjuntamente RF-007/RF-008/CS-007 sem ocultar divergências.

## Questões em Aberto / Bloqueios

| Item | Estado e efeito |
|---|---|
| B012-IMPLEMENTATION-BASELINE | A implementação F001–F011, lock, build PyInstaller e smoke local existem. Build de checkout limpo e compatibilidade em VMs por par aprovado ainda bloqueiam release. |
| B012-ARCH-MATRIX | Bloqueia matriz final e declaração de suporte. O plano mantém a matriz como entrada configurável pendente de aprovação humana. |
| B007-EBOOKLIB-LICENSE | Resolvido na F007: writer próprio com biblioteca padrão, sem EbookLib no lock ou artefato. |
| Inno Setup | Instalador opcional; validar licença aplicável e documentar versão/compilador antes de qualquer uso. Bundle portátil segue como saída-base. |
| Versões concretas | O ambiente local está travado em `uv.lock` e PyInstaller 6.22.3; conferir novamente a documentação e validar a matriz antes de release. |

## Notas de Revisão

- Consulta de documentação oficial feita em 2026-11-25; versões e termos devem ser revalidados na implementação/release.
- Em 2026-11-26, o build PyInstaller 6.22.3 foi executado no Windows 10 x64 local; a configuração usa hooks padrão, sem `--hidden-import` customizado. O bundle foi iniciado e o ciclo PowerShell foi automatizado em perfil temporário; os testes em VM limpa seguem pendentes.
- docs/roadmap.md não está no checkout. O escopo de F012 deriva da spec ativa e das specs F001–F011, sem inventar itens de roadmap.
