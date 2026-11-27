# Manga to Kindle — distribuição local de validação

Este pacote foi gerado para teste local em Windows 10 x64. Ele não é uma release aprovada e não declara suporte a outras combinações de Windows/arquitetura.

## Instalação por usuário

Em PowerShell, na pasta que contém este aviso, o ZIP e o script:

```powershell
$package = Get-ChildItem .\MangaToKindle-0.1.0-windows-x64-local-*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-MangaToKindle.ps1 -ArchivePath $package.FullName
```

O instalador confirma a instalação antes de extrair o bundle. O destino padrão é `%LOCALAPPDATA%\Programs\MangaToKindle`. Os dados da aplicação ficam no perfil local do usuário, fora da pasta de instalação.

## Atualização e remoção

Para atualizar, feche a aplicação e execute novamente o instalador com o novo ZIP. A versão anterior será preservada em uma pasta `MangaToKindle.previous-*` para recuperação manual.

Para remover somente os arquivos instalados, execute no PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Programs\MangaToKindle\Uninstall-MangaToKindle.ps1"
```

Digite a confirmação solicitada. A remoção preserva banco, biblioteca, originais, derivados, downloads, exports, preferências, logs e cache. O instalador não oferece remoção dos dados locais.

## Validação ainda pendente

O pacote ainda precisa de aprovação de arquitetura, revisão de licenças dos componentes empacotados e instalação/atualização/desinstalação em VMs limpas de Windows 10 e 11. Ele não está assinado digitalmente. Não distribua este rascunho como release.

O diretório também contém o inventário CycloneDX do lock e uma lista de declarações de licença encontradas na metadata instalada. Essa lista é evidência candidata para revisão; não substitui textos de licença, avisos completos nem aprovação jurídica.

O diretório contém ainda um inventário por caminho, tamanho e SHA-256 dos arquivos presentes no bundle `onedir`. Esse manifesto identifica os bytes distribuídos no rascunho, mas não determina a origem nem a licença de cada arquivo.

O arquivo `bundle-component-candidates.json` associa cada entrada física do bundle à origem candidata indicada pelo TOC do PyInstaller, aos metadados instalados do pacote ou aos caminhos do Python/Windows. Caminhos absolutos da máquina de build são removidos. Qualquer arquivo sem origem resolvida permanece explicitamente marcado; os metadados de licença ainda precisam de revisão humana e não substituem os avisos distribuídos.
