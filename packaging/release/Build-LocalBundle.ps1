[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$uvCommand = Get-Command uv -CommandType Application -ErrorAction Stop | Select-Object -First 1
$uvExecutable = $uvCommand.Source
$projectEnvironment = Join-Path $repositoryRoot '.venv'
$windowsRoot = $env:SystemRoot
if ([string]::IsNullOrWhiteSpace($windowsRoot)) {
    throw 'SystemRoot não está definido; não é possível isolar os caminhos de DLL do build.'
}

$environmentNames = @(
    'PATH',
    'VIRTUAL_ENV',
    'UV_PROJECT_ENVIRONMENT',
    'PYTHONHOME',
    'PYTHONPATH',
    'PYTHONNOUSERSITE',
    'QT_PLUGIN_PATH',
    'QT_QPA_PLATFORM_PLUGIN_PATH'
)
$savedEnvironment = @{}
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

try {
    $safePath = @(
        (Join-Path $projectEnvironment 'Scripts'),
        (Join-Path $windowsRoot 'System32'),
        $windowsRoot,
        (Join-Path $windowsRoot 'System32\Wbem'),
        (Join-Path $windowsRoot 'System32\WindowsPowerShell\v1.0')
    ) -join [IO.Path]::PathSeparator
    $env:PATH = $safePath
    Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
    $env:UV_PROJECT_ENVIRONMENT = $projectEnvironment
    foreach ($name in @(
        'PYTHONHOME',
        'PYTHONPATH',
        'PYTHONNOUSERSITE',
        'QT_PLUGIN_PATH',
        'QT_QPA_PLATFORM_PLUGIN_PATH'
    )) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }

    Push-Location $repositoryRoot
    try {
        & $uvExecutable sync --locked --python 3.12 --no-default-groups --group build
        if ($LASTEXITCODE -ne 0) { throw "uv sync falhou com código $LASTEXITCODE." }

        & $uvExecutable run --locked --python 3.12 --no-default-groups --group build pyinstaller --clean --noconfirm packaging/pyinstaller/MangaToKindle.spec
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou com código $LASTEXITCODE." }

        & $uvExecutable export --locked --format cyclonedx1.5 --no-default-groups --group build --output-file packaging/third-party-notices/dependency-inventory.cdx.json | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "A exportação CycloneDX falhou com código $LASTEXITCODE." }

        foreach ($module in @(
            'tools.release.license_inventory',
            'tools.release.bundle_inventory',
            'tools.release.component_inventory'
        )) {
            & $uvExecutable run --locked --python 3.12 --no-default-groups --group build python -m $module
            if ($LASTEXITCODE -ne 0) { throw "A geração de $module falhou com código $LASTEXITCODE." }
        }

        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'package-local-bundle.ps1')
        if ($LASTEXITCODE -ne 0) { throw "O empacotamento ZIP falhou com código $LASTEXITCODE." }
    }
    finally {
        Pop-Location
    }
}
finally {
    foreach ($name in $environmentNames) {
        $value = $savedEnvironment[$name]
        if ($null -eq $value) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        }
        else {
            [Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }
}
