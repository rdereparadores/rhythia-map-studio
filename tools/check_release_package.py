"""Check packaged executables from a temporary working directory, without Rhythia."""

import argparse
import json
import os
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path


def check_app(executable):
    with tempfile.TemporaryDirectory(prefix="rhythia-app-check-") as temporary:
        environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": ""}
        subprocess.run(
            [str(executable.resolve()), "--check-installation"],
            cwd=temporary,
            env=environment,
            check=True,
            timeout=60,
        )


def check_separator(directory):
    directory = directory.resolve()
    with tempfile.TemporaryDirectory(prefix="rhythia-separator-check-") as temporary:
        root = Path(temporary)
        samples = array("h", [0]) * (44100 * 3 * 2)
        for frame in range(0, 44100 * 3, 22050):
            for offset in range(100):
                samples[2 * (frame + offset)] = 12000
                samples[2 * (frame + offset) + 1] = 12000
        with wave.open(str(root / "input.wav"), "wb") as audio:
            audio.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
            audio.writeframes(samples.tobytes())
        output = root / "output"
        subprocess.run(
            [
                str(directory / "DemucsWorker/DemucsWorker.exe"),
                str(root / "input.wav"),
                str(output),
                str(directory / "models"),
            ],
            cwd=temporary,
            env={**os.environ, "PYTHONPATH": "", "CUDA_VISIBLE_DEVICES": "-1"},
            check=True,
            timeout=300,
        )
        import numpy as np
        import soundfile as sf

        result = json.loads((output / "result.json").read_text(encoding="utf-8"))
        if result["sr"] != 44100 or result["frames"] != 132300 or result["device"] != "cpu":
            raise ValueError(f"Unexpected separator output format or device: {result}")
        for name in ("vocals", "drums", "bass", "other"):
            data, rate = sf.read(output / f"{name}.wav")
            if rate != 44100 or data.shape != (132300, 2) or not np.isfinite(data).all():
                raise ValueError(f"Invalid separated track: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("app", "separator"))
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    {"app": check_app, "separator": check_separator}[arguments.kind](arguments.path)
