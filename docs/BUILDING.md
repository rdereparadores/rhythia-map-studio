# Building and packaging

All commands below run from the repository root in PowerShell. See the [README](../README.md) for basic installation and [CONTRIBUTING.md](../CONTRIBUTING.md) for development checks.

For automated tag-triggered builds and GitHub Releases, see [RELEASING.md](RELEASING.md).

## Build the desktop app

Install development dependencies, then select the interpreter explicitly:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.\build.ps1 -Python .\.venv\Scripts\python.exe
```

The default output is `dist/bin/RhythiaMapStudio/RhythiaMapStudio.exe`. `dist/Launch Map Studio.cmd` launches it. Distribute the entire application directory, including `_internal`.

Use `-OutputDirectory` to choose another destination. Builds without `-SeparatorPython` omit the optional separator. The script packages Qt assets and translation catalogs and removes a conflicting Poppler ICU DLL if one was collected from the build environment.

## Optional source separator

The separator uses Demucs 4.0.1 with the `htdemucs` model. Keep its dependencies in a separate Python 3.12 environment:

```powershell
py -3.12 -m venv .stems
.stems\Scripts\python -m pip install torch==2.5.1+cu124 torchaudio==2.5.1+cu124 --index-url https://download.pytorch.org/whl/cu124
.stems\Scripts\python -m pip install -r requirements-separator.txt
.\build.ps1 -Python .\.venv\Scripts\python.exe -SeparatorPython .\.stems\Scripts\python.exe
```

This downloads the model, verifies its pinned SHA-256 and packages the worker separately. The worker selects CUDA when available and CPU otherwise. CPU inference is slower.

A complete build has this layout:

```text
dist/
├── bin/RhythiaMapStudio/
├── separation/
│   ├── DemucsWorker/
│   ├── models/
│   └── backend.json
└── Launch Map Studio.cmd
```

The generated `backend.json` contains paths relative to its own directory:

```json
{
  "command": ["DemucsWorker/DemucsWorker.exe"],
  "models": "models",
  "cache": "cache"
}
```

Cached stems are verified before reuse. Deleting that cache forces separation to run again; it does not remove the model.

### Use a backend during development

After building the optional component, point the source app at its configuration:

```powershell
$env:RHYTHIA_SEPARATOR_CONFIG = (Resolve-Path .\dist\separation\backend.json).Path
.venv\Scripts\python run_studio.py
```

A local `separation/backend.json` in the repository is also supported. It is machine-specific and excluded from version control. Configurations may use different cache locations; the `cache` field is authoritative.

The checkpoint is pinned by `tools/prepare_models.py` and verified again before inference. See the [third-party notices](../THIRD_PARTY_NOTICES.md) for upstream references.

## Verify a package

Run the automated suite before building. Then check the packaged executable from PowerShell:

```powershell
$check = Start-Process -FilePath .\dist\bin\RhythiaMapStudio\RhythiaMapStudio.exe -ArgumentList '--check-installation' -PassThru -Wait
$check.ExitCode
```

An exit code of `0` indicates that the offline startup check passed. It exercises Qt, catalogs and assets without audio playback or persistent preferences. It does not test source separation, musical quality or compatibility with another Windows installation.

Before distributing a release, also verify:

- Startup on a clean Windows machine without the development environment.
- Song import, generation, playback, save/reopen and RHM export.
- Both UI languages and the basic/advanced views.
- Real separation, cancellation and cache reuse when shipping the optional backend.
- Required notices and licenses for the exact dependencies and model being distributed.

## Source and Python packages

Create a source-only archive using the explicit inclusion list:

```powershell
.venv\Scripts\python tools/source_archive.py dist/rhythia-map-studio-source.zip
```

It includes source, tests, documentation and project configuration. It excludes songs, map projects, local backend configuration, caches, binaries and downloaded models.

To build a Python wheel:

```powershell
.venv\Scripts\python -m pip wheel . --no-deps --wheel-dir dist/wheels
```

Development installation uses dependency ranges. Automated releases use the pinned
`requirements-release-app.txt` and `requirements-release-separator.txt` environments,
including transitive dependencies. Builds are not claimed to be byte-for-byte
reproducible. Release packages record the installed environment and dependency notices.
