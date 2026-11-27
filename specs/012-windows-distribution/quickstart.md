# Quickstart de Validação — F012

## Estado e escopo local

Existe um bundle `onedir` e um pacote local Windows 10 x64 com instalador, atualização e desinstalação por usuário. A pessoa usuária aprovou a matriz desejada Windows 10/11 x64 somente. O build, a inicialização real do executável, a migração local e o ciclo de instalação foram exercitados neste Windows 10 x64 com Python 3.12.16 e PyInstaller 6.22.3; Windows 11 x64 limpo ainda não foi validado. A decisão da matriz não aprova uma release nem prova compatibilidade.

O ZIP em `dist/local-release-draft` é um artefato de validação descartável, gerado no checkout atual. A revisão das licenças/avisos de terceiros e os testes em VMs limpas de Windows 10/11 x64 continuam pendentes. O CycloneDX, `dependency-license-candidates.json` e `bundle-component-candidates.json` contêm candidatos, não substituem `THIRD-PARTY-NOTICES` revisado. O inventário de proveniência associa arquivos nativos do Qt ao pacote e sua metadata instalada, sem concluir a licença. O instalador usa PowerShell por usuário; Inno Setup não foi usado. Nenhuma atualização remota é executada.

## Pré-requisitos

- Windows 10 x64 para reproduzir o build local validado. A matriz desejada aprovada é Windows 10/11 x64 somente; ela não declara compatibilidade comprovada antes das VMs limpas.
- Python 3.12 e `uv` no `PATH`.
- Checkout com `pyproject.toml` e `uv.lock` sincronizados.
- Fechar qualquer instância do Manga to Kindle antes de instalar, atualizar ou desinstalar.

## Executar a aplicação pelo checkout

Na raiz do projeto, no PowerShell:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O comando exato para iniciar o aplicativo pelo checkout é:

```powershell
uv run --locked --python 3.12 manga-to-kindle
```

## Build e geração do pacote local

Execute o script no PowerShell. Ele resolve somente as dependências do aplicativo e do grupo de build, restringe `PATH` para não coletar DLLs de runtimes externos, compila o bundle e gera SBOM e inventários:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\release\Build-LocalBundle.ps1
```

O script também compara os caminhos do TOC do PyInstaller com os arquivos reais do bundle e aborta se encontrar qualquer arquivo sem origem mapeada. Ele mantém o `PATH` original do PowerShell chamador depois que termina. O inventário de componentes não aprova licenças.

Para empacotar um bundle existente e inventários atualizados, execute:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\release\package-local-bundle.ps1
```

O resultado é um arquivo com timestamp em `dist/local-release-draft/MangaToKindle-0.1.0-windows-x64-local-*.zip`, acompanhado por scripts PowerShell, aviso local, CycloneDX, candidatos de licença copiados da metadata instalada, inventário de proveniência por arquivo e inventário por caminho/hash do bundle. Esses artefatos não aprovam licenças nem substituem avisos completos. Cada execução mantém os ZIPs anteriores e atualiza os arquivos auxiliares. O inventário de proveniência registra nomes de arquivos relativos, status de origem e candidatos de licença sem armazenar caminhos absolutos da máquina.

### Build isolado de inputs limpos

O teste de release prepara uma cópia temporária dos inputs do checkout, sincroniza o lock sem dependências de desenvolvimento e compila um bundle real. Execute-o separadamente porque compila todo o runtime PySide6:

```powershell
uv sync --locked --python 3.12
$env:M2K_RUN_CLEAN_BUILD_TEST = '1'
uv run --locked --python 3.12 pytest tests/packaging/test_release_from_clean_checkout.py -m release -q
Remove-Item Env:M2K_RUN_CLEAN_BUILD_TEST
```

Resultado Windows 10 x64: **1 passed em 94,71s**. O teste também compara os 222 caminhos mapeados com os arquivos físicos do bundle e exige zero origens não resolvidas. É um snapshot isolado do estado atual do checkout, não um commit limpo nem uma VM sem ferramentas de desenvolvimento.

### Validar e atestar um artefato de release

Depois que houver um manifest revisado que corresponda ao pacote, o utilitário calcula os hashes do manifest e do ZIP, confere a integridade/caminhos do arquivo e gera uma atestação. Os gates ficam `pending` por padrão. Só informe `passed` depois da evidência humana correspondente; com revisão de licenças aprovada, o utilitário verifica que os notices declarados estão dentro do ZIP.

```powershell
uv run --locked --no-sync --python 3.12 python -m tools.release.attestation `
  --manifest .\dist\release\release-manifest.json `
  --artifact-root .\dist\release `
  --artifact-name MangaToKindle.zip `
  --target-windows 'Windows 10' `
  --target-architecture x64 `
  --build-started-at-utc '2026-11-26T12:00:00Z' `
  --output .\dist\release\artifact-attestation.json
```

O checkout atual não possui manifest de release completo nem notices aprovados; esse comando é um roteiro para a etapa de aceitação e não foi executado contra o ZIP rascunho.

## Instalação, atualização e remoção por usuário

Selecione o ZIP mais recente, instale e responda `SIM` à confirmação:

```powershell
$package = Get-ChildItem .\dist\local-release-draft\MangaToKindle-0.1.0-windows-x64-local-*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\dist\local-release-draft\Install-MangaToKindle.ps1 -ArchivePath $package.FullName
```

O destino padrão dos executáveis é `%LOCALAPPDATA%\Programs\MangaToKindle`. A aplicação instalada inicia com:

```powershell
& "$env:LOCALAPPDATA\Programs\MangaToKindle\MangaToKindle.exe"
```

Para atualizar, feche o aplicativo e execute novamente o instalador com o novo pacote. O instalador conserva a pasta anterior com sufixo `.previous-*` para recuperação manual. Uma atualização que falha antes da extração mantém a versão instalada.

Para desinstalar somente executáveis e atalhos, responda `DESINSTALAR` à confirmação:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Programs\MangaToKindle\Uninstall-MangaToKindle.ps1"
```

A remoção padrão preserva banco, biblioteca, imagens, downloads, exports, perfis, preferências, logs e cache. O instalador não oferece remoção dos dados locais.

## Testes automatizados e perfil isolado

Antes de rodar testes após o build local, reative o grupo de desenvolvimento. A suíte end-to-end instala o ZIP recém-gerado em um diretório temporário e usa `MANGA_TO_KINDLE_DATA_ROOT` para não migrar o perfil real:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 pytest tests/packaging -q
uv run --locked --python 3.12 pytest tests -vv
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests tools
uv run --locked --python 3.12 mypy src/manga_to_kindle tools/release/bundle_inventory.py tools/release/license_inventory.py tools/release/manifest.py tools/release/attestation.py tools/release/component_inventory.py
```

Execução local em 2026-11-26: **34 testes de packaging passaram em 32,01s**, com um build lento ignorado por flag; o build lento passou separadamente em **94,71s**. A regressão completa teve **373 passed, 1 skipped em 139,00s**, incluindo KCC 13.0.4 real. Ruff concluiu com `All checks passed`; MyPy concluiu sem problemas nos 155 arquivos verificados. O ZIP real instalou, abriu, atualizou sem alterar o hash do banco e desinstalou preservando um sentinela. O bundle enumera **222 arquivos e 151.601.693 bytes**, todos mapeados por proveniência candidata; o build com `PATH` restrito não incluiu `ucrtbase.dll` externo nem shims API-set. O SBOM tem 24 componentes: 23 têm metadata candidata encontrada e `macholib==1.16.4` não está instalado neste host. Todas as revisões de licença continuam `pending`.

Revalidação em 27/11/2026: `uv run --locked --python 3.12 pytest tests/packaging -q` — **32 passed, 3 skipped em 33,71s**; `uv run --locked --python 3.12 pytest tests -q` — **369 passed, 5 skipped em 99,39s**; smoke de inicialização/composição — **2 passed em 3,24s**. Os três skips de packaging requerem build PyInstaller, ZIP local ou habilitação explícita do build isolado; não foram tratados como sucesso do pacote instalado. O resultado de startup usa perfil temporário e comprova o app local, não instalação em VM limpa. A execução desta revalidação não configurou o binário KCC real.

O smoke visual do executável foi feito no Windows 10 x64 usando `MANGA_TO_KINDLE_DATA_ROOT` apontado para uma pasta temporária. A fixture foi consultada somente por escolha explícita; Atualizações mostrou seu estado local depois de navegar e novamente após reiniciar, e Downloads não apresentou fonte autorizada. A fixture foi usada apenas para verificar apresentação, persistência e isolamento. Não foi usada para comprovar integração remota, download ou refresh.

Para iniciar manualmente o executável com uma raiz de QA descartável:

```powershell
$env:MANGA_TO_KINDLE_DATA_ROOT = Join-Path $env:TEMP 'MangaToKindle-F012-QA'
& "$env:LOCALAPPDATA\Programs\MangaToKindle\MangaToKindle.exe"
```

`MANGA_TO_KINDLE_DATA_ROOT` precisa ser um caminho absoluto. Sem essa variável, o aplicativo segue usando `QStandardPaths.AppLocalDataLocation` no perfil local do Windows.

## Funcionalidades disponíveis para teste

- Bundle PyInstaller real `onedir`, ícone e metadados PE locais.
- Inventário de origem candidata para cada entrada do bundle e inventário de caminhos, tamanhos e SHA-256; ambos vêm do build real e não aprovam licenças.
- Instalação por usuário, atualização com cópia anterior preservada e desinstalação sem remover dados.
- Verificação de ZIP contra traversal, destinos absolutos, caminhos duplicados e links simbólicos.
- Smoke do executável no perfil isolado e inicialização da migração `0011_mobi_export_artifacts`.
- Tela Atualizações integrada ao bundle: mostra estado local e mantém ações remotas indisponíveis sem provedor real autorizado.
- Teste end-to-end do ZIP local: instalar, abrir, conferir migração e desinstalar preservando um dado sentinela.
- Build local isolado do `PATH` externo, proveniência total 222/222 e comparação exata de caminhos com hashes do bundle.

## Funcionalidades ainda não disponíveis como release

- Matriz registrada: Windows 10/11 x64 somente. A matriz não declara compatibilidade comprovada.
- Instalação, upgrade e remoção em VMs limpas Windows 10/11 x64 sem Python, `uv`, Qt ou ferramentas de desenvolvimento.
- Revisão de licenças, textos de licença e `THIRD-PARTY-NOTICES` completos para os componentes efetivamente empacotados.
- Assinatura digital, release publicada, installer Inno Setup, auto-update e targets ARM64/x86.

F005 (fluxo de download pela aplicação) continua pendente de integração end-to-end. F010 (atualização periódica) não está autorizada pelo escopo NDL. O instalador e o bundle local funcionam no host validado, mas não são uma release aprovada.

## Critérios de aceitação que exigem validação manual

- Em Windows 10 x64 e Windows 11 x64, validar instalação limpa sem Python/uv/Qt, ícone, versão, primeira abertura e encerramento.
- Confirmar navegação e funções principais com dependências opcionais ausentes, incluindo KCC e navegador; o primeiro início não deve abrir rede.
- Instalar uma versão anterior com dados sintéticos, atualizar e comparar IDs, relações, caminhos, preferências e checksums; simular migração interrompida e confirmar recuperação do backup.
- Validar app aberto, cancelamento, espaço insuficiente, arquivos em uso, permissões de usuário e caminho com espaços/acentos.
- Desinstalar, conferir remoção de atalhos/registro e comparar a base e os dados antes/depois; reinstalar e abrir a biblioteca preservada.
- Conferir metadados e ícone do EXE, assinatura/SmartScreen e notices por dependência; registrar hashes e evidências em [checklist de release](checklists/release.md).
- Confirmar no Windows 11 x64 limpo; o teste local atual cobre somente Windows 10 x64.

## Recuperação

- Instalações anteriores do aplicativo ficam em `MangaToKindle.previous-*`; comparar a versão desejada antes de restaurar manualmente.
- Migrações da aplicação fazem backup local antes de alterar uma base existente e interrompem o início se a recuperação falhar.
- Nunca use arquivos pessoais, livros reais, credenciais ou serviços externos nos testes de release.
- Mantenha pendente na checklist qualquer critério manual que não tenha evidência executada.

## Referências

- [Checklist de release](checklists/release.md)
- [Contrato de ciclo do instalador](contracts/installer-lifecycle.md)
- [Manifest de release](contracts/release-manifest.schema.json)
- [Atestação de artefato](contracts/artifact-attestation.schema.json)
- [Modelo de dados](data-model.md)
- [Plano](plan.md)
