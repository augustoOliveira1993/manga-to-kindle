[CmdletBinding()]
param(
    [string] $RegistryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MangaToKindle',

    [string] $ShortcutDirectory = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'),

    [switch] $ConfirmUninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $RegistryPath)) {
    throw 'O registro de instalação do Manga to Kindle não foi encontrado.'
}
$registration = Get-ItemProperty -LiteralPath $RegistryPath
$installDirectory = [System.IO.Path]::GetFullPath([string] $registration.InstallLocation).TrimEnd('\')
$userRoot = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd('\')
$userPrefix = $userRoot + '\'
if (
    -not $installDirectory.StartsWith($userPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
    $installDirectory -eq $userRoot
) {
    throw 'O caminho registrado não é uma pasta de instalação segura do perfil local.'
}
$userDataRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $env:LOCALAPPDATA 'MangaToKindle\MangaToKindle')
).TrimEnd('\')
if (
    $installDirectory.StartsWith(($userDataRoot + '\'), [System.StringComparison]::OrdinalIgnoreCase) -or
    $userDataRoot.StartsWith(($installDirectory + '\'), [System.StringComparison]::OrdinalIgnoreCase) -or
    $installDirectory -eq $userDataRoot
) {
    throw 'O caminho da instalação se sobrepõe à pasta de dados e não será removido.'
}
if (-not (Test-Path -LiteralPath $installDirectory -PathType Container)) {
    throw 'A pasta de instalação registrada não existe; nenhuma outra pasta foi removida.'
}
$installItem = Get-Item -LiteralPath $installDirectory -Force
if (($installItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'A pasta de instalação é um link ou junction e não será removida.'
}
$markerPath = Join-Path $installDirectory 'manga-to-kindle.install.json'
if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
    throw 'A pasta não tem o marcador esperado; nenhuma remoção foi feita.'
}
$marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
if ($marker.product_id -cne 'manga-to-kindle') {
    throw 'O marcador não pertence ao Manga to Kindle; nenhuma remoção foi feita.'
}
if (Get-Process -Name 'MangaToKindle' -ErrorAction SilentlyContinue) {
    throw 'Feche o Manga to Kindle antes de desinstalar.'
}

if (-not $ConfirmUninstall) {
    Write-Host "A pasta de instalação a remover é: $installDirectory"
    Write-Host 'A biblioteca, exports, preferências, logs e cache locais serão preservados.'
    $answer = Read-Host 'Digite DESINSTALAR para remover somente os arquivos instalados'
    if ($answer -cne 'DESINSTALAR') {
        Write-Host 'Desinstalação cancelada; nenhum arquivo foi alterado.'
        exit 0
    }
}

$removed = $false
for ($attempt = 1; $attempt -le 6; $attempt++) {
    try {
        if (Test-Path -LiteralPath $installDirectory) {
            Remove-Item -LiteralPath $installDirectory -Recurse -Force -ErrorAction Stop
        }
        if (-not (Test-Path -LiteralPath $installDirectory)) {
            $removed = $true
            break
        }
    }
    catch {
        if ($attempt -eq 6) {
            throw 'Não foi possível remover os arquivos instalados. Feche o aplicativo e tente novamente.'
        }
    }
    if ($attempt -lt 6) {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $removed) {
    throw 'Não foi possível remover os arquivos instalados. Feche o aplicativo e tente novamente.'
}

$shortcutPath = Join-Path $ShortcutDirectory 'Manga to Kindle.lnk'
if (Test-Path -LiteralPath $shortcutPath -PathType Leaf) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcutTarget = [System.IO.Path]::GetFullPath([string] $shortcut.TargetPath)
    $expectedTarget = [System.IO.Path]::GetFullPath((Join-Path $installDirectory 'MangaToKindle.exe'))
    if ($shortcutTarget -eq $expectedTarget) {
        Remove-Item -LiteralPath $shortcutPath -Force
    }
}
Remove-Item -LiteralPath $RegistryPath -Recurse -Force
Write-Host 'Manga to Kindle foi desinstalado. Os dados locais foram preservados.'
