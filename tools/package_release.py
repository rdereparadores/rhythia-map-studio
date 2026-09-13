"""Create size-checked release archives and a SHA-256 manifest."""

import argparse
import hashlib
import zipfile
from pathlib import Path

from release_version import package_version
from source_archive import source_files

MAX_ASSET_BYTES = 2 * 1024**3


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def create_archive(root, destination, exclude=()):
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if path.is_file() and relative.parts[0] not in exclude:
                archive.write(path, relative.as_posix())
    if destination.stat().st_size >= MAX_ASSET_BYTES:
        raise ValueError(f"Release asset exceeds GitHub's size limit: {destination.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("app", "separator", "checksums"))
    parser.add_argument("--input", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, default=Path("release-assets"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    version = package_version()
    if args.kind == "app":
        create_archive(
            args.input,
            args.output / f"RhythiaMapStudio-{version}-windows-x64.zip",
            exclude=("separation",),
        )
        with zipfile.ZipFile(
            args.output / f"RhythiaMapStudio-{version}-source.zip", "w", zipfile.ZIP_DEFLATED
        ) as archive:
            root = Path(__file__).resolve().parents[1]
            for path in source_files():
                archive.write(path, path.relative_to(root).as_posix())
    elif args.kind == "separator":
        create_archive(args.input, args.output / f"RhythiaMapStudio-{version}-separator-cpu-windows-x64.zip")
    else:
        assets = sorted(args.output.glob("*.zip"))
        expected = {
            f"RhythiaMapStudio-{version}-{suffix}.zip"
            for suffix in ("windows-x64", "source", "separator-cpu-windows-x64")
        }
        if {path.name for path in assets} != expected:
            raise ValueError("Missing or unexpected release assets.")
        if any(path.stat().st_size >= MAX_ASSET_BYTES for path in assets):
            raise ValueError("Release asset exceeds GitHub's size limit.")
        (args.output / "SHA256SUMS.txt").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in assets), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
