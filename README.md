# Manga to Kindle

Aplicativo desktop local para organizar mangás e preparar conteúdo para leitura em dispositivos Kindle. Este checkout contém a fundação F001, a interface F002 e o catálogo de demonstração offline de F003/F004. Provedores reais, downloads, processamento de imagens, exportação e envio ainda não estão disponíveis.

## Requisitos

- Windows 10 ou Windows 11.
- Python 3.12 ou superior.
- `uv` instalado e disponível no `PATH`.

As dependências e versões resolvidas ficam em `pyproject.toml` e `uv.lock`. Não atualize o lock durante uma instalação normal.

## Instalação e execução

No PowerShell, na raiz do projeto:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

A janela inicial é exibida enquanto diretórios, configuração e banco local são preparados fora da thread gráfica. A interface oferece Biblioteca, Adicionar mangá, Downloads, Conversão e Configurações. Em Adicionar mangá, a consulta suportada é somente a fixture sintética `https://fixture.invalid/manga/demo`; ela mostra e persiste metadados fictícios, capítulos e seleção no banco local. URLs externas não usam dados de demonstração e são recusadas sem rede. Downloads e conversões seguem como simulações; nenhuma página é baixada e nenhum livro é exportado ou enviado.

Atalhos de navegação: `Ctrl+1` Biblioteca, `Ctrl+2` Adicionar mangá, `Ctrl+3` Downloads, `Ctrl+4` Conversão e `Ctrl+5` Configurações. Na seleção de capítulos, `Espaço` alterna o capítulo focado; os controles também podem ser usados com mouse e Tab. O tema claro/escuro fica em Configurações e é salvo na configuração local.

## Dados locais

O aplicativo usa `QStandardPaths.AppLocalDataLocation`. No Windows, com os nomes atuais da aplicação, o caminho resolvido é normalmente:

```text
%LOCALAPPDATA%\MangaToKindle\MangaToKindle\
```

Dentro dessa raiz são criadas:

- `config\settings.json`: tema e limites locais de rotação dos logs, sem credenciais.
- `data\manga_to_kindle.sqlite3`: base SQLite e seu esquema versionado, incluindo snapshots locais do catálogo de demonstração quando consultado.
- `data\manga_to_kindle.sqlite3.migration-backup`: backup da base anterior durante migrações.
- `logs\application.log`: log rotativo local.
- `cache\`: reservado para cache local; F001 não armazena conteúdo de mangá.

A configuração padrão mantém arquivos de log de até 5 MiB e três cópias rotacionadas. Uma configuração inválida é preservada; o aplicativo não a substitui silenciosamente. A F003/F004 armazena apenas o snapshot sintético retornado pelo provider fixture; a URL original não é persistida. Nenhum conteúdo de página é armazenado.

## Qualidade e testes

```powershell
uv run --locked --python 3.12 pytest tests/unit tests/integration tests/acceptance/foundation tests/ui
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os testes usam bases e diretórios temporários e não acessam serviços externos. Consulte o [quickstart da F004](specs/004-catalog-chapters/quickstart.md) para consulta offline, ordenação e seleção, o [quickstart da F003](specs/003-extensible-providers/quickstart.md) para contratos e segurança dos provedores, o [quickstart da F002](specs/002-desktop-interface/quickstart.md) para navegação/acessibilidade, e o [quickstart da F001](specs/001-app-foundation/quickstart.md) para migrações, recuperação e encerramento.

## Privacidade e diagnóstico

Configuração, banco e logs permanecem no perfil local do usuário. Logs removem URLs, credenciais, caminhos absolutos e campos identificados como conteúdo. Nenhuma credencial ou conteúdo de livro é armazenado pelas features atuais. Em falha de migração, o aplicativo interrompe a inicialização e tenta restaurar o backup local; não exclua a base nem o arquivo de backup durante a recuperação.

## Desenvolvimento

Camadas: `domain`, `application`, `infrastructure` e `presentation`. O domínio não importa Qt nem SQLAlchemy. A UI e o bootstrap executam operações potencialmente bloqueantes em workers Qt. Código e identificadores usam inglês; interface e documentação voltada à pessoa usuária usam português brasileiro. Consulte [AGENTS.md](AGENTS.md) e a [constituição](.specify/memory/constitution.md) antes de contribuir.
