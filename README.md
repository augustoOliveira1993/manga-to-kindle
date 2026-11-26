# Manga to Kindle

Aplicativo desktop local para organizar mangás e preparar conteúdo para leitura em dispositivos Kindle. Este checkout contém a fundação F001, a interface F002, o catálogo offline de F003/F004, a fila local F005, a importação/processamento de imagens F006, exportação local EPUB/CBZ F007 e Biblioteca local F008. A F005 ainda aguarda fonte autorizada; o envio ao Kindle e o instalador Windows continuam pendentes.

## Estado de implementação

O marco **F002 — protótipo visual navegável** está disponível. A F003 entrega a fixture offline e a F004 fecha o fluxo local de catálogo, ordenação, seleção e atualização recuperável. A F006 importa imagens locais autorizadas e prepara derivados 600×800. O marco **F007 — MVP com geração EPUB** cria e valida arquivos locais EPUB 3 de layout fixo e CBZ. A F008 conecta a Biblioteca aos registros locais, com busca, filtros, disponibilidade, histórico e remoção confirmada. Os marcos F005, F009 e F012 ainda dependem de gates próprios descritos abaixo.

| Feature | Disponível para teste |
|---|---|
| F001 — Fundação | Inicialização, persistência local, configuração e encerramento seguro. |
| F002 — Interface | Navegação desktop, estados de interface, acessibilidade por teclado e tema. |
| F003 — Provedores | Provedor `fixture.invalid`, IDs determinísticos e rejeição de URLs sem provedor; sem rede. |
| F004 — Catálogo | Consulta offline, ordenação numérica/especial, seleção por intervalo e atualização preservando o último catálogo válido. |
| F005 — Fila de downloads | Fila SQLite, progresso por capítulo/página, pausa, retomada explícita, cancelamento, retry, validação raster e recuperação. O motor é verificado com transporte de teste isolado; a aplicação não tem fonte autorizada e não inicia downloads reais. |
| F006 — Importação de imagens | Pastas/CBZ (JPEG, PNG, WEBP), ordenação revisável, autorização, originais preservados, prévia 600×800 em escala de cinza, recorte opcional e divisão RTL/LTR. Limites: 5.000 imagens, 25 MiB por imagem, 2 GiB por origem e 50 megapixels por imagem. |
| F007 — Exportação | EPUB 3 fixo e CBZ a partir de páginas F006 processadas; capítulo/volume, RTL/LTR no EPUB, divisão por tamanho, validação interna, staging e histórico SQLite. KCC não está configurado; compatibilidade com dispositivo não foi validada. |
| F008 — Biblioteca local | Busca sem distinção de acentos/caixa, filtros combináveis, favoritos, ordenação, disponibilidade por arquivo/hash, histórico de F005–F007 e remoção com escopo confirmado. Não consulta rede nem carrega fixtures automaticamente. |
| F009–F012 | Fluxo de envio, atualizações de capítulos, perfis completos e instalador Windows continuam pendentes; F009 é a próxima feature desbloqueada. |

O marco **F005 — primeiro download funcional** continua pendente até haver uma fonte cuja autorização cubra o download e o uso local pretendido. O transporte de teste não conta como download funcional. F007 cria EPUBs localmente, sem declarar compatibilidade com Kindle físico ou firmware. A F008 está integrada à UI; seus critérios manuais e resultados automatizados estão em [specs/implementation-checkpoint.md](specs/implementation-checkpoint.md) e [quickstart F008](specs/008-local-library/quickstart.md).

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

O segundo comando é o comando exato para iniciar a aplicação após a instalação.

A janela inicial é exibida enquanto diretórios, configuração, banco local e recuperação das filas são preparados fora da thread gráfica. A interface oferece Biblioteca, Adicionar mangá, Downloads, Conversão, Configurações e Importar imagens. Em Adicionar mangá, a consulta suportada é somente a fixture sintética `https://fixture.invalid/manga/demo`; ela mostra e persiste metadados fictícios e capítulos no banco local. A seleção de capítulos permanece na tela. URLs externas sem provedor não usam dados de demonstração e são recusadas sem rede. A tela Downloads consulta trabalhos persistidos e mostra progresso por capítulo e página; a fixture não autoriza downloads, então o botão de início permanece indisponível e nenhuma conexão é aberta. Os transportes falsos existem apenas nos testes automatizados.

Em **Importar imagens**, escolha uma pasta local ou CBZ autorizado. A tela valida JPEG, PNG e WEBP, apresenta ordem natural que pode ser alterada, permite confirmar um destino local e exibe a prévia derivada 600×800 em escala de cinza. Recorte de margens e divisão de páginas duplas começam desativados; direção RTL/LTR só se aplica às páginas marcadas. O app preserva os bytes originais e grava originais/derivados sob `data\images\imports`; nenhum arquivo de demonstração é copiado para o perfil automaticamente. Há exemplos sintéticos seguros em [examples/demo-import](examples/demo-import).

Em **Conversão**, marque capítulos com todas as páginas processadas, escolha uma pasta local, formato EPUB ou CBZ, agrupamento e, se necessário, limite por arquivo. EPUB exige idioma explícito e registra RTL/LTR; CBZ mantém a ordem dos nomes de página, enquanto cada leitor controla sua direção de navegação. Arquivos existentes não são substituídos. Consulte o [quickstart F007](specs/007-epub-kcc-export/quickstart.md).

Em **Biblioteca**, pesquise mangá, autor, capítulo, número e volume; combine favoritos, disponibilidade, estado de download e exportação; consulte Histórico e revise remoção de registros/arquivos antes de confirmar. Os arquivos sem vínculo podem ser revisados e removidos individualmente depois. Dados de demonstração da F003 aparecem identificados e só são persistidos após consulta explícita; a biblioteca não preenche exemplos por conta própria. O [quickstart F008](specs/008-local-library/quickstart.md) descreve o roteiro e os limites exatos de exclusão.

Atalhos de navegação: `Ctrl+1` Biblioteca, `Ctrl+2` Adicionar mangá, `Ctrl+3` Downloads, `Ctrl+4` Conversão, `Ctrl+5` Configurações e `Ctrl+6` Importar imagens. Na seleção de capítulos, `Espaço` alterna o capítulo focado; os controles também podem ser usados com mouse e Tab. O tema claro/escuro fica em Configurações e é salvo na configuração local.

## Dados locais

O aplicativo usa `QStandardPaths.AppLocalDataLocation`. No Windows, com os nomes atuais da aplicação, o caminho resolvido é normalmente:

```text
%LOCALAPPDATA%\MangaToKindle\MangaToKindle\
```

Dentro dessa raiz são criadas:

- `config\settings.json`: tema e limites locais de rotação dos logs, sem credenciais.
- `data\manga_to_kindle.sqlite3`: base SQLite e seu esquema versionado, incluindo snapshots locais do catálogo de demonstração quando consultado.
- A revisão `0006_library` armazena favoritos, preferências de busca, snapshots mínimos de identidade de histórico e diário recuperável de exclusões. Pesquisa e histórico consultam os registros originadores, sem duplicar bytes.
- `data\downloads\`: destino gerenciado para páginas autorizadas e arquivos temporários isolados; permanece vazio enquanto nenhuma fonte autorizada estiver habilitada.
- `data\images\imports\`: originais e derivados de importações locais autorizadas. A área `data\images\.staging\` contém apenas lotes ainda não publicados e é reconciliada na inicialização.
- O banco registra plano, estado e checksums das exportações F007. Arquivos EPUB/CBZ são gravados somente na pasta escolhida pela pessoa usuária; a exportação não copia arquivos de demonstração nem altera originais.
- `data\manga_to_kindle.sqlite3.migration-backup`: backup da base anterior durante migrações.
- `logs\application.log`: log rotativo local.
- `cache\`: reservado para cache local; F001 não armazena conteúdo de mangá.

A configuração padrão mantém arquivos de log de até 5 MiB e três cópias rotacionadas. Uma configuração inválida é preservada; o aplicativo não a substitui silenciosamente. A F003/F004 armazena apenas o snapshot sintético retornado pelo provider fixture; a URL original não é persistida. A F005 preserva os bytes originais em `data\downloads\` somente depois de autorização, validação de formato e finalização atômica. A F006 grava originais e imagens derivadas em pastas distintas dentro de `data\images\imports\` e não modifica a origem.

## Qualidade e testes

```powershell
uv run --locked --python 3.12 pytest tests -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os testes usam bases e diretórios temporários e não acessam serviços externos. Consulte os [quickstarts F008](specs/008-local-library/quickstart.md), [F007](specs/007-epub-kcc-export/quickstart.md), [F006](specs/006-image-import-processing/quickstart.md), [F005](specs/005-download-queue/quickstart.md), [F004](specs/004-catalog-chapters/quickstart.md), [F003](specs/003-extensible-providers/quickstart.md), [F002](specs/002-desktop-interface/quickstart.md) e [F001](specs/001-app-foundation/quickstart.md) para os respectivos roteiros e critérios manuais.

O motor de fila, política de retry, integridade de arquivos e recuperação usam exclusivamente transporte e respostas de teste; eles não habilitam uma fonte real.

## Privacidade e diagnóstico

Configuração, banco e logs permanecem no perfil local do usuário. Logs removem URLs, credenciais, caminhos absolutos e campos identificados como conteúdo. A F007 grava o arquivo final na pasta local escolhida e mantém apenas metadados/checksums do histórico no banco; não envia conteúdo pela rede. Em falha de migração, o aplicativo interrompe a inicialização e tenta restaurar o backup local; não exclua a base nem o arquivo de backup durante a recuperação.

## Desenvolvimento

Camadas: `domain`, `application`, `infrastructure` e `presentation`. O domínio não importa Qt nem SQLAlchemy. A UI e o bootstrap executam operações potencialmente bloqueantes em workers Qt. Código e identificadores usam inglês; interface e documentação voltada à pessoa usuária usam português brasileiro. Consulte [AGENTS.md](AGENTS.md) e a [constituição](.specify/memory/constitution.md) antes de contribuir.
