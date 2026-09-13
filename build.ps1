param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'dist'),
    [string]$Python = 'python',
    [string]$SeparatorPython = ''
)
$ErrorActionPreference = 'Stop'
$appName = 'RhythiaMapStudio'
$appArguments = @(
    '-m', 'PyInstaller', '--clean', '--noconfirm', '--windowed', '--onedir',
    '--name', $appName,
    '--paths', "$PSScriptRoot/src",
    '--add-data', "$PSScriptRoot/src/rhythia_studio/ui/assets;rhythia_studio/ui/assets",
    '--add-data', "$PSScriptRoot/src/rhythia_studio/locales;rhythia_studio/locales",
    '--distpath', "$OutputDirectory/bin",
    '--workpath', "$PSScriptRoot/build/app",
    '--specpath', "$PSScriptRoot/build"
)
foreach ($module in @('torch', 'torchaudio', 'matplotlib', 'pandas', 'sklearn', 'librosa', 'numba', 'tkinter', 'IPython', 'pytest')) {
    $appArguments += @('--exclude-module', $module)
}
& $Python @appArguments "$PSScriptRoot/run_studio.py"
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller could not build the application.' }
Copy-Item -LiteralPath "$PSScriptRoot/LICENSE", "$PSScriptRoot/THIRD_PARTY_NOTICES.md", "$PSScriptRoot/README.md", "$PSScriptRoot/I18N.md", "$PSScriptRoot/ARCHITECTURE.md", "$PSScriptRoot/CONTRIBUTING.md", "$PSScriptRoot/CHANGELOG.md" -Destination $OutputDirectory -Force
Copy-Item -LiteralPath "$PSScriptRoot/docs" -Destination $OutputDirectory -Recurse -Force
# Qt targets Windows ICU; a same-named Poppler ICU on PATH is incompatible.
$studioIcu = Join-Path $OutputDirectory "bin/$appName/_internal/icuuc.dll"
if (Test-Path -LiteralPath $studioIcu) { Remove-Item -LiteralPath $studioIcu }
if ($SeparatorPython) {
    & $SeparatorPython "$PSScriptRoot/tools/prepare_models.py" "$OutputDirectory/separation/models"
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the model.' }
    $separatorArguments = @(
        '-m', 'PyInstaller', '--noconfirm', '--onedir', '--console', '--name', 'DemucsWorker',
        '--distpath', "$OutputDirectory/separation", '--workpath', "$PSScriptRoot/build/separator",
        '--specpath', "$PSScriptRoot/build", '--collect-submodules', 'demucs', '--collect-data', 'demucs',
        '--collect-data', 'julius', '--hidden-import', 'numpy.core.multiarray'
    )
    foreach ($module in @('matplotlib', 'pandas', 'sklearn', 'torchvision', 'tensorflow', 'tensorboard', 'IPython', 'pytest')) {
        $separatorArguments += @('--exclude-module', $module)
    }
    & $SeparatorPython @separatorArguments "$PSScriptRoot/tools/separate_worker.py"
    if ($LASTEXITCODE -ne 0) { throw 'Could not package the separator.' }
    [IO.File]::WriteAllText((Join-Path $OutputDirectory 'separation/backend.json'), '{"command":["DemucsWorker/DemucsWorker.exe"],"models":"models","cache":"cache"}')
}
[IO.File]::WriteAllText((Join-Path $OutputDirectory 'Launch Map Studio.cmd'), "@echo off`r`nstart `"`" `"%~dp0bin\$appName\$appName.exe`"`r`n")
Write-Output "Application built at $OutputDirectory/bin/$appName"
