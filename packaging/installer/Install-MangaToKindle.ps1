[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ArchivePath,

    [string] $InstallDirectory = (Join-Path $env:LOCALAPPDATA 'Programs\MangaToKindle'),

    [string] $RegistryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MangaToKindle',

    [string] $ShortcutDirectory = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'),

    [switch] $ConfirmInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-FullDirectoryPath([string] $Path) {
    if (-not [System.IO.Path]::IsPathRooted($Path)) {
        throw 'O diretório de instalação precisa ser absoluto.'
    }
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetPathRoot($fullPath)
    if ($fullPath -eq $root) {
        return $fullPath
    }
    return $fullPath.TrimEnd('\')
}

function Test-PathWithin([string] $Child, [string] $Parent) {
    $parentPrefix = $Parent.TrimEnd('\') + '\'
    return $Child.StartsWith($parentPrefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Expand-SafeArchive([string] $Path, [string] $DestinationDirectory) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $seen = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::OrdinalIgnoreCase
        )
        $entries = [System.Collections.Generic.List[object]]::new()
        $hasExecutable = $false
        foreach ($entry in $archive.Entries) {
            $name = $entry.FullName.Replace('\', '/')
            if (
                [System.IO.Path]::IsPathRooted($name) -or
                $name.Contains(':') -or
                @($name.Split('/') | Where-Object { $_ -in @('.', '..') }).Count -gt 0
            ) {
                throw 'O pacote contém um caminho inseguro.'
            }
            if (-not $seen.Add($name)) {
                throw 'O pacote contém caminhos duplicados.'
            }
            $unixType = ($entry.ExternalAttributes -shr 16) -band 0xF000
            if ($unixType -eq 0xA000) {
                throw 'O pacote contém um link simbólico não permitido.'
            }
            $entries.Add($entry)
            if ($name -ceq 'MangaToKindle.exe') {
                $hasExecutable = $true
            }
        }
        if (-not $hasExecutable) {
            throw 'O pacote não contém o executável MangaToKindle.exe na raiz.'
        }

        $destinationRoot = [System.IO.Path]::GetFullPath($DestinationDirectory).TrimEnd('\') + '\'
        foreach ($entry in $entries) {
            $relativeName = $entry.FullName.Replace('\', '/').Replace('/', '\')
            $destinationPath = [System.IO.Path]::GetFullPath(
                (Join-Path $DestinationDirectory $relativeName)
            )
            if ($destinationPath.Length -gt 259) {
                throw 'O caminho extraído excede o limite suportado pelo instalador do Windows.'
            }
            if (-not $destinationPath.StartsWith(
                $destinationRoot,
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
                throw 'O pacote contém um caminho fora do diretório de instalação.'
            }
            if ($entry.FullName.EndsWith('/') -or $entry.FullName.EndsWith('\')) {
                [System.IO.Directory]::CreateDirectory($destinationPath) | Out-Null
                continue
            }

            $destinationParent = [System.IO.Path]::GetDirectoryName($destinationPath)
            [System.IO.Directory]::CreateDirectory($destinationParent) | Out-Null
            $inputStream = $entry.Open()
            $outputStream = [System.IO.File]::Open(
                $destinationPath,
                [System.IO.FileMode]::CreateNew
            )
            try {
                $inputStream.CopyTo($outputStream)
            }
            finally {
                $outputStream.Dispose()
                $inputStream.Dispose()
            }
        }
    }
    finally {
        $archive.Dispose()
    }
}

if (-not $ConfirmInstall) {
    $answer = Read-Host 'Instalar Manga to Kindle para este usuário? Digite SIM para continuar'
    if ($answer -cne 'SIM') {
        Write-Host 'Instalação cancelada; nenhum arquivo foi alterado.'
        exit 0
    }
}

$archive = [System.IO.Path]::GetFullPath($ArchivePath)
$target = Get-FullDirectoryPath $InstallDirectory
$parent = [System.IO.Path]::GetDirectoryName($target)
$userRoot = Get-FullDirectoryPath $env:LOCALAPPDATA
$userPrefix = $userRoot.TrimEnd('\') + '\'
$dataRoot = Get-FullDirectoryPath (Join-Path $env:LOCALAPPDATA 'MangaToKindle\MangaToKindle')
$stageId = [Guid]::NewGuid().ToString('N').Substring(0, 16)
$stage = Join-Path $parent ('.m2k-stage-' + $stageId)
$backup = $null
$published = $false

if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
    throw 'O arquivo do pacote não foi encontrado.'
}
if (
    $target -eq $parent -or
    $target -eq [System.IO.Path]::GetPathRoot($target) -or
    $target -eq ([System.IO.Path]::GetPathRoot($target)).TrimEnd('\')
) {
    throw 'O diretório escolhido não pode ser uma raiz ou pasta-pai do sistema.'
}
if (
    -not $target.StartsWith($userPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
    $target -eq $userRoot
) {
    throw 'A instalação precisa ficar dentro do perfil local deste usuário.'
}
if (
    $target -eq $dataRoot -or
    (Test-PathWithin $target $dataRoot) -or
    (Test-PathWithin $dataRoot $target)
) {
    throw 'A instalação precisa ficar separada da pasta local de dados do aplicativo.'
}
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
if (Test-Path -LiteralPath $target) {
    $targetItem = Get-Item -LiteralPath $target -Force
    if (($targetItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'O diretório de instalação não pode ser um link ou junction.'
    }
    $markerPath = Join-Path $target 'manga-to-kindle.install.json'
    if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
        throw 'O destino já contém dados sem identificação do Manga to Kindle; nada foi sobrescrito.'
    }
    $marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
    if ($marker.product_id -cne 'manga-to-kindle') {
        throw 'O destino pertence a outro produto; nada foi sobrescrito.'
    }
}
if (Get-Process -Name 'MangaToKindle' -ErrorAction SilentlyContinue) {
    throw 'Feche o Manga to Kindle antes de instalar ou atualizar.'
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'Uninstall-MangaToKindle.ps1'))) {
    throw 'O pacote de instalação está incompleto: script de desinstalação ausente.'
}

New-Item -ItemType Directory -Path $stage | Out-Null
try {
    Expand-SafeArchive $archive $stage
    $executable = Join-Path $stage 'MangaToKindle.exe'
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw 'A extração não produziu o executável esperado.'
    }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Uninstall-MangaToKindle.ps1') -Destination $stage
    $installMarker = @{
        product_id = 'manga-to-kindle'
        version = '0.1.0'
    } | ConvertTo-Json
    Set-Content -LiteralPath (Join-Path $stage 'manga-to-kindle.install.json') -Value $installMarker -Encoding UTF8

    if (Test-Path -LiteralPath $target) {
        $backup = $target + '.previous-' + [Guid]::NewGuid().ToString('N')
        Move-Item -LiteralPath $target -Destination $backup
    }
    try {
        Move-Item -LiteralPath $stage -Destination $target
        $published = $true
    }
    catch {
        if ($backup -and (Test-Path -LiteralPath $backup) -and -not (Test-Path -LiteralPath $target)) {
            Move-Item -LiteralPath $backup -Destination $target
            $backup = $null
        }
        throw
    }

    New-Item -ItemType Directory -Path $ShortcutDirectory -Force | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $shortcutPath = Join-Path $ShortcutDirectory 'Manga to Kindle.lnk'
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $target 'MangaToKindle.exe'
    $shortcut.WorkingDirectory = $target
    $shortcut.IconLocation = (Join-Path $target 'MangaToKindle.exe') + ',0'
    $shortcut.Description = 'Aplicativo local Manga to Kindle'
    $shortcut.Save()

    New-Item -ItemType Directory -Path (Split-Path -Parent $RegistryPath) -Force | Out-Null
    New-Item -Path $RegistryPath -Force | Out-Null
    Set-ItemProperty -LiteralPath $RegistryPath -Name 'DisplayName' -Value 'Manga to Kindle'
    Set-ItemProperty -LiteralPath $RegistryPath -Name 'DisplayVersion' -Value '0.1.0'
    Set-ItemProperty -LiteralPath $RegistryPath -Name 'InstallLocation' -Value $target
    Set-ItemProperty -LiteralPath $RegistryPath -Name 'UninstallString' -Value (
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' +
        (Join-Path $target 'Uninstall-MangaToKindle.ps1') + '"'
    )
    Write-Host "Manga to Kindle instalado em: $target"
    if ($backup) {
        Write-Host "A versão anterior foi preservada em: $backup"
    }
    Write-Host 'A biblioteca e as preferências locais ficam fora da pasta de instalação.'
}
catch {
    if ($published -and (Test-Path -LiteralPath $target) -and $backup) {
        $failedInstall = $target + '.failed-' + [Guid]::NewGuid().ToString('N')
        Move-Item -LiteralPath $target -Destination $failedInstall
        Move-Item -LiteralPath $backup -Destination $target
        $backup = $null
        Write-Host "A nova instalação foi preservada para diagnóstico em: $failedInstall"
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $stage) {
        $resolvedStage = [System.IO.Path]::GetFullPath($stage)
        if (-not (Test-PathWithin $resolvedStage $parent)) {
            throw 'O staging saiu do diretório temporário esperado; ele foi preservado.'
        }
        $stageItem = Get-Item -LiteralPath $resolvedStage -Force
        if (($stageItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'O staging virou link ou junction; ele foi preservado.'
        }
        Remove-Item -LiteralPath $resolvedStage -Recurse -Force
    }
}
