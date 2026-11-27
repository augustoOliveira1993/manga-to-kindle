[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$distRoot = Join-Path $repositoryRoot 'dist'
$bundle = Join-Path $repositoryRoot 'dist\MangaToKindle'
$draft = Join-Path $repositoryRoot 'dist\local-release-draft'
$runId = [Guid]::NewGuid().ToString('N')
$stagedBundle = Join-Path $draft ('.MangaToKindle-stage-' + $runId)
$buildTimestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$archive = Join-Path $draft "MangaToKindle-0.1.0-windows-x64-local-$buildTimestamp.zip"

function Get-NormalizedPath([string] $Path) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if ($fullPath -eq [System.IO.Path]::GetPathRoot($fullPath)) {
        return $fullPath
    }
    return $fullPath.TrimEnd('\')
}

function Test-PathWithin([string] $Child, [string] $Parent) {
    $parentPrefix = (Get-NormalizedPath $Parent).TrimEnd('\') + '\'
    $childPath = Get-NormalizedPath $Child
    return $childPath.StartsWith($parentPrefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Assert-NotReparsePoint([string] $Path) {
    if (Test-Path -LiteralPath $Path) {
        $item = Get-Item -LiteralPath $Path -Force
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Caminho de staging/saída não pode ser link ou junction: $Path"
        }
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $bundle 'MangaToKindle.exe') -PathType Leaf)) {
    throw 'Execute o build PyInstaller antes de empacotar a distribuição local.'
}
foreach ($inventoryName in @(
    'dependency-inventory.cdx.json',
    'dependency-license-candidates.json',
    'bundle-file-inventory.json',
    'bundle-component-candidates.json'
)) {
    $inventoryPath = Join-Path (
        Join-Path $repositoryRoot 'packaging\third-party-notices'
    ) $inventoryName
    if (-not (Test-Path -LiteralPath $inventoryPath -PathType Leaf)) {
        throw "Gere o inventário de dependências antes de empacotar: $inventoryName"
    }
}
$inventoryDirectory = Join-Path $repositoryRoot 'packaging\third-party-notices'
$componentInventory = Get-Content -LiteralPath (Join-Path $inventoryDirectory 'bundle-component-candidates.json') -Raw | ConvertFrom-Json
$bundleInventory = Get-Content -LiteralPath (Join-Path $inventoryDirectory 'bundle-file-inventory.json') -Raw | ConvertFrom-Json
if ($componentInventory.provenance_status -ne 'mapped' -or $componentInventory.unresolved_file_count -ne 0) {
    throw 'O inventário de componentes ainda contém arquivos sem origem mapeada.'
}
if ($componentInventory.file_count -ne $bundleInventory.file_count) {
    throw 'Os inventários de componentes e arquivos não cobrem a mesma quantidade de entradas.'
}
$bundlePathIndex = @{}
foreach ($file in $bundleInventory.files) {
    $bundlePathIndex[[string]$file.path] = $true
}
foreach ($file in $componentInventory.files) {
    if (-not $bundlePathIndex.ContainsKey([string]$file.bundle_path)) {
        throw "O caminho de proveniência não existe no bundle: $($file.bundle_path)"
    }
}
if (-not (Test-Path -LiteralPath $distRoot -PathType Container)) {
    throw 'A pasta dist do build não foi encontrada.'
}
if (-not (Test-PathWithin $draft $distRoot)) {
    throw 'O diretório de rascunho precisa ficar dentro de dist.'
}
if (Test-Path -LiteralPath $draft) {
    Assert-NotReparsePoint $draft
}
New-Item -ItemType Directory -Path $draft -Force | Out-Null
if (-not (Test-PathWithin $stagedBundle $draft)) {
    throw 'O staging precisa ficar dentro do diretório de rascunho.'
}
try {
    New-Item -ItemType Directory -Path $stagedBundle | Out-Null
    Get-ChildItem -LiteralPath $bundle -Force -Recurse | ForEach-Object {
        if (($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "O bundle contém um link ou junction não permitido: $($_.FullName)"
        }
    }
    Copy-Item -Path (Join-Path $bundle '*') -Destination $stagedBundle -Recurse -Force

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $stagedBundle,
        $archive,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'packaging\installer\Install-MangaToKindle.ps1') -Destination $draft -Force
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'packaging\installer\Uninstall-MangaToKindle.ps1') -Destination $draft -Force
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'packaging\release\LOCAL-BUILD-NOTICE.md') -Destination $draft -Force
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'packaging\third-party-notices\dependency-inventory.cdx.json') -Destination $draft -Force
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'packaging\third-party-notices\dependency-license-candidates.json') -Destination $draft -Force
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'packaging\third-party-notices\bundle-file-inventory.json') -Destination $draft -Force
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'packaging\third-party-notices\bundle-component-candidates.json') -Destination $draft -Force

    $hash = Get-FileHash -LiteralPath $archive -Algorithm SHA256
    Write-Host "Bundle local criado: $archive"
    Write-Host "SHA-256: $($hash.Hash.ToLowerInvariant())"
    Write-Host 'Os inventários CycloneDX, de origem e de arquivos não substituem avisos nem revisão de licenças.'
    Write-Host 'Este rascunho não é uma release aprovada.'
}
finally {
    if (Test-Path -LiteralPath $stagedBundle) {
        Assert-NotReparsePoint $stagedBundle
        if (Test-PathWithin $stagedBundle $draft) {
            Remove-Item -LiteralPath $stagedBundle -Recurse -Force
        }
    }
}
