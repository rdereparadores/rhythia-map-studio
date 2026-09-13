"""Preserve installed dependency notices and record the exact build environment."""

import argparse
import json
import re
import shutil
from importlib import metadata
from pathlib import Path


def collect(destination):
    destination.mkdir(parents=True, exist_ok=True)
    inventory = []
    for distribution in sorted(metadata.distributions(), key=lambda item: item.metadata["Name"].lower()):
        name = distribution.metadata["Name"]
        folder = destination / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        folder.mkdir(exist_ok=True)
        notices = []
        for file in distribution.files or []:
            if not any(part.lower().startswith(("license", "copying", "notice")) for part in file.parts):
                continue
            source = Path(distribution.locate_file(file))
            if source.is_file():
                relative = Path(*(part if part != ".." else "_parent" for part in file.parts))
                target = folder / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                notices.append(relative.as_posix())
        raw_metadata = distribution.read_text("METADATA") or distribution.read_text("PKG-INFO")
        if raw_metadata is None:
            raw_metadata = json.dumps(dict(distribution.metadata), indent=2)
        (folder / "METADATA.txt").write_text(raw_metadata, encoding="utf-8")
        inventory.append(dict(name=name, version=distribution.version, notices=notices))
    (destination / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    collect(parser.parse_args().destination)
