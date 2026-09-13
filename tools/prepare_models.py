"""Fetch the pinned official model; inference itself is completely offline."""

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

CHECKPOINT = "955717e8-8726e21a.th"
SHA256 = "8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4"
URL = "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/" + CHECKPOINT


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    checkpoint = destination / CHECKPOINT
    if not checkpoint.exists():
        temporary = checkpoint.with_suffix(".download")
        urllib.request.urlretrieve(URL, temporary)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != SHA256:
            raise ValueError("The downloaded model does not match its pinned SHA-256.")
        temporary.replace(checkpoint)
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != SHA256:
        raise ValueError("The existing model does not match its pinned SHA-256.")
    configuration = destination / "htdemucs.yaml"
    configuration.write_text("models: [955717e8]\n", encoding="utf-8")
    manifest = dict(
        model="htdemucs",
        files={
            CHECKPOINT: SHA256,
            configuration.name: hashlib.sha256(configuration.read_bytes()).hexdigest(),
        },
    )
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
