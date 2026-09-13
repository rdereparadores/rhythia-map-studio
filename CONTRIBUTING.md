# Contributing

Thank you for helping improve Rhythia Map Studio. Contributions can include bug reports, mapping improvements, tests, translations and documentation.

## Development setup

Use Windows and Python 3.12 for the documented development environment. From the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python run_studio.py
```

The optional separator is configured separately; see [BUILDING.md](docs/BUILDING.md). It is not required for the automated test suite.

## Report a bug

Open an issue with:

- App version, Windows version and whether you run from source or a packaged build.
- Steps to reproduce, expected behavior and actual behavior.
- Relevant settings, including difficulty, tempo and whether source separation is enabled.
- For musical issues, the approximate timestamp and a description of the timing or movement problem.

Include a minimal example when possible. Use synthetic audio or material you may redistribute. Project files embed the original song; inspect logs for personal paths before sharing them. Errors are recorded in `studio.log` in the application data directory selected by Qt.

For substantial algorithm or workflow changes, describe the proposed behavior in an issue before investing in a large implementation.

## Submit a pull request

1. Make a focused change on a branch in your fork.
2. Add or update tests for the behavior being changed.
3. Run the checks below.
4. Update the relevant documentation and add an entry under **Unreleased** in the changelog.
5. Explain the problem, resulting behavior and validation in the pull request description.

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m ruff check src tests tools run_studio.py
.venv\Scripts\python -m ruff format --check src tests tools run_studio.py
```

GitHub Actions is configured to run style checks, tests and Python package construction on Windows with Python 3.11 and 3.12. Passing tests does not replace manual musical evaluation.

## Code conventions

- Write identifiers, comments, docstrings and developer documentation in English. Prefer descriptive names and explicit contracts.
- Keep audio analysis and document operations independent of Qt. Consult [ARCHITECTURE.md](ARCHITECTURE.md) before choosing a module.
- Separate structural refactors from musical tuning changes so output comparisons remain meaningful.
- Preserve project compatibility, cancellation behavior and edits outside regenerated regions.
- Keep user-facing text in the translation system. Use English message keys and canonical IDs. Follow [I18N.md](I18N.md).
- Keep the UI automatic by default; put specialist controls in Advanced options.
- Do not launch Rhythia from application code or automated tests.

Do not commit virtual environments, models, caches, generated binaries, personal configuration, songs or map projects. Tests generate temporary synthetic audio.

## Versioning and license

The package version is defined in `src/rhythia_studio/__init__.py`. Change it when preparing a release, not for every documentation edit. Document-schema versions are separate from the application version. The loader accepts only the current schema.

Contributions to original project code use GPL-3.0-only. Preserve third-party attribution and identify the source and license of any external code or assets you introduce.
