"""Create a source-only archive from explicit roots, excluding local user data."""

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    "README.md",
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
    "I18N.md",
    "CHANGELOG.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
    "requirements-separator.txt",
    "requirements-release-app.txt",
    "requirements-release-separator.txt",
    "build.ps1",
    "run_studio.py",
    "Launch Map Studio.cmd",
    ".gitignore",
    ".gitattributes",
)
SOURCE_ROOTS = ("src/rhythia_studio", "tests", "tools", "docs", ".github")
SOURCE_EXTENSIONS = {".py", ".json", ".svg", ".yml", ".yaml", ".md"}


def source_files():
    for name in ROOT_FILES:
        yield ROOT / name
    for folder in SOURCE_ROOTS:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix in SOURCE_EXTENSIONS:
                yield path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_files():
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(args.destination)


if __name__ == "__main__":
    main()
