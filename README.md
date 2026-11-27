# Manga to Kindle

Aplicativo desktop local para organizar mangás e preparar conteúdo para leitura em dispositivos Kindle. Este checkout contém a fundação F001, a interface F002, fixture offline e provedor NDL limitado em F003/F004, fila local com download real de itens individuais PDM F005, importação/processamento de imagens F006, exportação local EPUB/CBZ e MOBI opcional via KCC externo F007, Biblioteca F008, fluxo F009 manual ou SMTP opt-in, infraestrutura local de atualização F010, configurações/perfis F011 e um bundle Windows local com scripts de instalação F012. Atualizações remotas periódicas F010 não estão autorizadas. A distribuição F012 ainda é um rascunho, não uma release aprovada.

## Estado de implementação

O marco **F002 — protótipo visual navegável** está disponível. A F003 oferece consulta pontual de metadados da NDL para itens individuais PDM, além da fixture offline. A F004 fecha o fluxo local de catálogo, ordenação, seleção e atualização recuperável. O marco **F005 — primeiro download funcional** baixa um item NDL PDM selecionado e confirmado, valida páginas e as grava atomicamente no perfil local. A F006 importa imagens autorizadas com 600×800 por padrão e aceita dimensões do perfil escolhido. O marco **F007 — MVP funcional com geração EPUB** cria e valida EPUB 3 e CBZ locais; a opção MOBI usa a CLI KCC 13.0.4 escolhida pela pessoa usuária. A F008 conecta a Biblioteca aos registros locais. A F009 implementa a abertura manual do Send to Kindle e o envio SMTP opcional com TLS, confirmação por tentativa e histórico sanitizado. A F011 integra perfis de dispositivo, preferências de pasta/cache e restauração sem perda. A F012 já gera um bundle `onedir` e instala/atualiza/remove os arquivos do aplicativo sem apagar os dados do usuário; matriz aprovada: Windows 10/11 x64 somente. A release aguarda revisão de licenças e VMs limpas.

| Feature | Disponível para teste |
|---|---|
| F001 — Fundação | Inicialização, persistência local, configuração e encerramento seguro. |
| F002 — Interface | Navegação desktop, estados de interface, acessibilidade por teclado e tema. |
| F003 — Provedores | Fixture offline e consulta real pontual à NDL para um item PDM escolhido pelo usuário. Catálogos modernos e outras fontes não estão integrados; atualização periódica é desativada. |
| F004 — Catálogo | Consulta offline, ordenação numérica/especial, seleção por intervalo e atualização preservando o último catálogo válido. |
| F005 — Fila de downloads | Fila SQLite, progresso por capítulo/página, pausa, retomada explícita, cancelamento, retry, validação raster, recuperação e download real de item NDL PDM após consentimento. O item de QA `851650` concluiu 33/33 páginas em perfil temporário. |
| F006 — Importação de imagens | Pastas/CBZ (JPEG, PNG, WEBP), ordenação revisável, autorização, originais preservados, prévia 600×800 em escala de cinza, recorte opcional e divisão RTL/LTR. Limites: 5.000 imagens, 25 MiB por imagem, 2 GiB por origem e 50 megapixels por imagem. |
| F007 — Exportação | EPUB 3 fixo e CBZ; MOBI com KCC CLI 13.0.4 selecionada explicitamente. Agrupamento, RTL/LTR, limites suportados, staging e histórico SQLite. MOBI validado nos perfis 600×800/K810 e 1072×1448/KPW34; compatibilidade física ainda não validada. |
| F008 — Biblioteca local | Busca sem distinção de acentos/caixa, filtros combináveis, favoritos, ordenação, disponibilidade por arquivo/hash, histórico de F005–F007 e remoção com escopo confirmado. Não consulta rede nem carrega fixtures automaticamente. |
| F009 — Envio ao Kindle | Abertura manual de pasta/página oficial; SMTP opt-in com Windows Credential Manager, TLS obrigatório, consentimento por tentativa e histórico que não afirma entrega. Nenhuma conta Amazon/SMTP pública ou Kindle foi contatado; validação visual Windows pendente. |
| F010 — Atualizações de capítulos | Tela de estado/histórico (recarregada ao abrir), IDs estáveis, persistência transacional, avisos locais por capítulo, controles opt-in e scheduler em processo estão implementados. Atualização manual/periódica fica desabilitada sem adapter não simulado, autorização de consulta, limite por provedor e política de intervalo documentada. A fixture nunca habilita nem prova F010. |
| F011 — Configurações e perfis | Perfis Básico 8ª/10ª e Paperwhite 10ª, perfis personalizados, seleção aplicada a novos trabalhos, caminhos, concorrência, cache por manifesto e restauração sem apagar conteúdo. |
| F012 — Distribuição | Bundle PyInstaller `onedir` e scripts PowerShell de instalação, atualização e remoção por usuário. A matriz aprovada é Windows 10/11 x64; licenças e instalação em VMs limpas seguem pendentes. |

F005 concluiu o primeiro download funcional com 33/33 páginas de um item NDL PDM selecionado, validado e gravado em perfil temporário. A validação manual da interface Windows continua descrita no quickstart, sem bloquear as próximas features. F007 cria EPUBs localmente, sem declarar compatibilidade com Kindle físico ou firmware. F009 pode iniciar uma transferência autorizada ao SMTP configurado, mas um aceite SMTP não comprova entrega no Kindle. O bundle F012 é um rascunho local Windows 10/11 x64 e não deve ser distribuído como release. Critérios manuais e resultados automatizados estão em [specs/implementation-checkpoint.md](specs/implementation-checkpoint.md) e nos [quickstarts das features](specs/012-windows-distribution/quickstart.md).

## Requisitos

- Windows 10 ou Windows 11, x64. ARM64 e x86 não fazem parte da matriz aprovada.
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

A janela inicial é exibida enquanto diretórios, configuração, banco local e recuperação das filas são preparados fora da thread gráfica. A interface oferece Biblioteca, Adicionar mangá, Downloads, Conversão, Configurações, Importar imagens e Atualizações. Em **Adicionar mangá**, as fontes listadas são: fixture offline `https://fixture.invalid/manga/demo` e consulta pontual da NDL `https://lab.ndl.go.jp/dl/book/<ID>` para metadados de item individual do acervo Public Domain Mark. A consulta NDL só ocorre ao clicar; o transporte valida host, DNS, IP conectado e TLS. Redirects só seguem para o host IIIF e o bucket de entrega NDL exato após revalidação; qualquer outro destino é recusado. O app aplica intervalo local de 60 segundos entre consultas de metadados e até 12 requests ao endpoint IIIF por minuto; são limites locais, não cotas da NDL. Outros catálogos não estão integrados e a NDL não faz atualização periódica. A fixture mostra dados fictícios e persiste em registro isolado do item real. Em **Downloads**, selecione item NDL PDM e confirme para iniciar; as páginas ficam no perfil local. Consulte o [quickstart F003](specs/003-extensible-providers/quickstart.md) e o [quickstart F005](specs/005-download-queue/quickstart.md).

Em **Importar imagens**, escolha uma pasta local ou CBZ autorizado. A tela valida JPEG, PNG e WEBP, apresenta ordem natural que pode ser alterada, permite confirmar um destino local e mostra a prévia no perfil escolhido (600×800 para o Básico 10ª por padrão). Recorte de margens e divisão de páginas duplas começam desativados; direção RTL/LTR só se aplica às páginas marcadas. O app preserva os bytes originais e grava originais/derivados sob `data\images\imports`; nenhum arquivo de demonstração é copiado para o perfil automaticamente. Há exemplos sintéticos seguros em [examples/demo-import](examples/demo-import).

Em **Conversão**, marque capítulos com todas as páginas processadas, escolha uma pasta local, formato EPUB, CBZ ou MOBI, agrupamento e, se necessário, limite por arquivo. MOBI exige uma CLI KCC 13.0.4 selecionada e aceita somente perfis 600×800 ou 1072×1448; não aceita divisão por tamanho. EPUB e MOBI exigem idioma explícito; RTL/LTR é enviado ao KCC. KCC não é baixado nem instalado pelo app. Arquivos existentes não são substituídos. Consulte o [quickstart F007](specs/007-epub-kcc-export/quickstart.md).

Em **Biblioteca**, pesquise mangá, autor, capítulo, número e volume; combine favoritos, disponibilidade, estado de download e exportação; consulte Histórico e revise remoção de registros/arquivos antes de confirmar. Os arquivos sem vínculo podem ser revisados e removidos individualmente depois. Dados de demonstração da F003 aparecem identificados e só são persistidos após consulta explícita; a biblioteca não preenche exemplos por conta própria. O [quickstart F008](specs/008-local-library/quickstart.md) descreve o roteiro e os limites exatos de exclusão.

Em **Enviar ao Kindle**, a opção manual abre a pasta validada do EPUB e a página oficial, deixando seleção e upload sob controle da pessoa usuária. O canal SMTP é opcional, exige TLS validado e consentimento específico para cada tentativa; a senha fica no Gerenciador de Credenciais do Windows. O teste de conexão não envia e-mail, e o histórico registra somente aceitação/rejeição observada pelo servidor, com destino mascarado. Consulte o [quickstart F009](specs/009-kindle-send/quickstart.md) para testes locais e critérios manuais.

Em **Configurações**, selecione um dos três perfis internos ou duplique um para editar resolução, orientação, margens, recorte e qualidade aplicável. Os perfis são usados em novas importações e exports; snapshots e arquivos já existentes não mudam. As pastas de downloads, exports e cache precisam existir, ser locais e não se sobrepor. A limpeza remove somente prévias/miniaturas íntegros e registrados no manifesto; nenhuma outra pasta ou arquivo é varrido. Restaurar padrões exige confirmação e preserva biblioteca, exports, perfis personalizados e referências de credenciais. Confira o [quickstart F011](specs/011-settings-profiles/quickstart.md) para o roteiro e limites manuais.

## Distribuição local F012 (rascunho)

No PowerShell, na raiz do checkout, gere o bundle e o pacote de validação:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\release\Build-LocalBundle.ps1
```

O script usa apenas o grupo de build e restringe o `PATH` dos subprocessos ao ambiente do projeto e aos diretórios do Windows, evitando coletar DLLs de runtimes de ferramentas externas. Ele gera CycloneDX, candidatos de licença e proveniência por entrada do TOC do PyInstaller, compara os caminhos com o bundle real e cria o ZIP com esses inventários como sidecars. A análise de proveniência remove caminhos absolutos e não aprova licenças.

Para compilar os inputs em um snapshot temporário sem reaproveitar `.venv`, `dist` ou `build`, execute o teste lento no Windows:

```powershell
uv sync --locked --python 3.12
$env:M2K_RUN_CLEAN_BUILD_TEST = '1'
uv run --locked --python 3.12 pytest tests/packaging/test_release_from_clean_checkout.py -m release -q
Remove-Item Env:M2K_RUN_CLEAN_BUILD_TEST
```

O script [`tools/release/attestation.py`](tools/release/attestation.py) verifica os hashes do manifest e do ZIP e mantém a atestação `pending` até que os gates de arquitetura, licença e VM sejam aprovados. A release atual não tem manifest completo nem notices revisados; o ZIP local permanece um rascunho.

Cada execução cria um ZIP com timestamp. Selecione o mais recente e instale para o usuário atual, confirmando a pergunta apresentada pelo script:

```powershell
$package = Get-ChildItem .\dist\local-release-draft\MangaToKindle-0.1.0-windows-x64-local-*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\dist\local-release-draft\Install-MangaToKindle.ps1 -ArchivePath $package.FullName
```

O executável instalado pode ser iniciado com `& "$env:LOCALAPPDATA\Programs\MangaToKindle\MangaToKindle.exe"`. Para atualizar, feche o app e rode novamente o instalador com o novo ZIP; a cópia anterior dos executáveis fica em `MangaToKindle.previous-*`. Para remover só os arquivos instalados, sem apagar a biblioteca:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Programs\MangaToKindle\Uninstall-MangaToKindle.ps1"
```

O [quickstart F012](specs/012-windows-distribution/quickstart.md) registra os testes locais, os comandos e os critérios manuais. O build exclui o grupo de desenvolvimento e inclui inventários de arquivos/hashes e de origem candidata que cobrem cada arquivo do bundle real; nada disso substitui avisos de terceiros revisados. A matriz aprovada é Windows 10/11 x64; compatibilidade em VMs limpas e revisão de licenças permanecem pendentes.

Atalhos de navegação: `Ctrl+1` Biblioteca, `Ctrl+2` Adicionar mangá, `Ctrl+3` Downloads, `Ctrl+4` Conversão, `Ctrl+5` Enviar ao Kindle, `Ctrl+6` Configurações, `Ctrl+7` Importar imagens e `Ctrl+8` Atualizações. Na seleção de capítulos, `Espaço` alterna o capítulo focado; os controles também podem ser usados com mouse e Tab. O tema claro/escuro fica em Configurações e é salvo na configuração local.

## Dados locais

O aplicativo usa `QStandardPaths.AppLocalDataLocation`. No Windows, com os nomes atuais da aplicação, o caminho resolvido é normalmente:

```text
%LOCALAPPDATA%\MangaToKindle\MangaToKindle\
```

Para smoke tests/QA, `MANGA_TO_KINDLE_DATA_ROOT` pode apontar para outra pasta, desde que seja um caminho absoluto. Sem essa variável, a aplicação usa o perfil local padrão do Windows.

Dentro dessa raiz são criadas:

- `config\settings.json`: tema e limites locais de rotação dos logs, sem credenciais.
- `data\manga_to_kindle.sqlite3`: base SQLite e seu esquema versionado, incluindo snapshots locais do catálogo de demonstração quando consultado.
- A revisão `0008_settings` persiste perfis/preferências e manifesto de cache; `0009_profile_dimensions` permite que F006/F007 usem dimensões além do padrão 600×800 sem reescrever páginas antigas. `0010_catalog_updates` adiciona IDs estáveis de origem, histórico de consultas, preferências por mangá e avisos locais; `0011_mobi_export_artifacts` permite registrar os MOBI F007.
- A revisão `0006_library` armazena favoritos, preferências de busca, snapshots mínimos de identidade de histórico e diário recuperável de exclusões. Pesquisa e histórico consultam os registros originadores, sem duplicar bytes.
- `data\downloads\`: destino gerenciado para páginas autorizadas e arquivos temporários isolados; permanece vazio enquanto nenhuma fonte autorizada estiver habilitada.
- `data\images\imports\`: originais e derivados de importações locais autorizadas. A área `data\images\.staging\` contém apenas lotes ainda não publicados e é reconciliada na inicialização.
- O banco registra plano, estado e checksums das exportações F007. Arquivos EPUB/CBZ/MOBI são gravados somente na pasta escolhida pela pessoa usuária; o staging KCC copia páginas processadas, não copia demonstrações automaticamente e não altera originais.
- A revisão `0007_transfers` persiste perfil SMTP sem segredo e histórico mínimo de tentativas; o destino do histórico fica mascarado. Senhas não entram em SQLite, arquivos de configuração ou logs.
- `data\manga_to_kindle.sqlite3.migration-backup`: backup da base anterior durante migrações.
- `logs\application.log`: log rotativo local.
- `cache\`: raiz padrão do cache. Somente categorias `preview` e `thumbnail` registradas no manifesto podem ser limpas; não há produtores de cache de produto habilitados na versão atual.

A configuração padrão mantém arquivos de log de até 5 MiB e três cópias rotacionadas; as preferências F011 ficam no banco local e o tema continua em `config\settings.json`. Uma configuração inválida é preservada; o aplicativo não a substitui silenciosamente. A F003/F004 armazena o snapshot retornado pela fixture ou pelo item NDL consultado; a URL de entrada não é persistida. A fila guarda PID, IDs estáveis de página e snapshot da política de autorização, sem persistir URL de redirect ou query assinada; referências são reconstruídas após reinício sem nova consulta. A F005 publica bytes somente depois de validar autorização, formato e finalização atômica. A F006 grava originais e imagens derivadas em pastas distintas e não modifica a origem.

## Qualidade e testes

```powershell
uv run --locked --python 3.12 pytest tests -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests tools
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Revalidação em 27/11/2026: a suíte completa passou com **369 testes aprovados e 5 ignorados** (`uv run --locked --python 3.12 pytest tests -q`); o smoke de inicialização/composição desktop passou com **2 testes** (`uv run --locked --python 3.12 pytest tests/acceptance/foundation/test_desktop_startup.py tests/integration/test_desktop_startup.py -q`). Os ignorados requerem KCC real configurado, build/pacote local, habilitação explícita do teste de build isolado ou suporte do host a symlinks. Esses resultados validam os fluxos locais exercitados; não comprovam fonte autorizada para download/atualização, entrega externa ao Kindle ou compatibilidade física.

Os testes usam bases e diretórios temporários e não acessam serviços externos; a integração SMTP usa somente servidor TLS local em loopback. Os testes F010 usam provedores locais isolados para validar políticas, transações e a interface, sem demonstrar autorização ou compatibilidade de uma fonte real. O teste end-to-end do instalador usa o ZIP local gerado antes pelo comando acima e um perfil descartável. Consulte os [quickstarts F012](specs/012-windows-distribution/quickstart.md), [F011](specs/011-settings-profiles/quickstart.md), [F010](specs/010-chapter-updates/quickstart.md), [F009](specs/009-kindle-send/quickstart.md), [F008](specs/008-local-library/quickstart.md), [F007](specs/007-epub-kcc-export/quickstart.md), [F006](specs/006-image-import-processing/quickstart.md), [F005](specs/005-download-queue/quickstart.md), [F004](specs/004-catalog-chapters/quickstart.md), [F003](specs/003-extensible-providers/quickstart.md), [F002](specs/002-desktop-interface/quickstart.md) e [F001](specs/001-app-foundation/quickstart.md) para os respectivos roteiros e critérios manuais.

Para compilar os inputs do bundle em um snapshot temporário isolado no Windows, execute o teste lento de release:

```powershell
$env:M2K_RUN_CLEAN_BUILD_TEST = '1'
uv run --locked --no-sync --python 3.12 pytest tests/packaging/test_release_from_clean_checkout.py -m release -q
Remove-Item Env:M2K_RUN_CLEAN_BUILD_TEST
```

O teste sincroniza as dependências travadas de produção/build e executa o PyInstaller sem reutilizar o ambiente ou os artefatos do checkout. Isso não substitui a validação em VMs limpas Windows 10/11 x64 nem aprova licenças.

O motor de fila, política de retry, integridade de arquivos e recuperação usam exclusivamente transporte e respostas de teste; eles não habilitam uma fonte real.

## Privacidade e diagnóstico

Configuração, banco e logs permanecem no perfil local do usuário. Logs removem URLs, credenciais, caminhos absolutos e campos identificados como conteúdo. A F007 grava o arquivo final na pasta local escolhida e mantém apenas metadados/checksums do histórico no banco; não envia conteúdo pela rede. Em falha de migração, o aplicativo interrompe a inicialização e tenta restaurar o backup local; não exclua a base nem o arquivo de backup durante a recuperação.

## Desenvolvimento

Camadas: `domain`, `application`, `infrastructure` e `presentation`. O domínio não importa Qt nem SQLAlchemy. A UI e o bootstrap executam operações potencialmente bloqueantes em workers Qt. Código e identificadores usam inglês; interface e documentação voltada à pessoa usuária usam português brasileiro. Consulte [AGENTS.md](AGENTS.md) e a [constituição](.specify/memory/constitution.md) antes de contribuir.
