"""Isolated local separator process with cancellable execution and verified disk cache.

The UI process never imports torch. The backend and model are an independently
packaged component; an explicit local config supports development installations.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import soundfile as sf

from .messages import MessageError
from .models import check_cancel
from .musical_features import SOURCES


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def config_path():
    explicit = os.environ.get("RHYTHIA_SEPARATOR_CONFIG")
    if explicit:
        return Path(explicit)
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parents[2]
    for base in (root, root.parent, root.parent.parent):
        candidate = base / "separation" / "backend.json"
        if candidate.is_file():
            return candidate
    return None


def available():
    configuration = config_path()
    return configuration is not None and configuration.is_file()


class SeparationEngine:
    def __init__(self, configuration=None):
        self.configuration = Path(configuration) if configuration else config_path()

    def separate(self, path, progress=lambda s: None, cancel=lambda: False):
        check_cancel(cancel)
        if self.configuration is None or not self.configuration.exists():
            raise ValueError(
                "The separation component was not found. Keep the separation folder alongside the app."
            )
        config = json.loads(self.configuration.read_text(encoding="utf-8"))
        base = self.configuration.parent
        command = [str((base / p).resolve()) if not Path(p).is_absolute() else p for p in config["command"]]
        model_dir = (base / config["models"]).resolve()
        cache = (base / config["cache"]).resolve()
        model_fingerprint = file_hash(model_dir / "manifest.json")
        key = hashlib.sha256((file_hash(path) + model_fingerprint + "separator-v1").encode()).hexdigest()
        target = cache / key
        manifest_path = target / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if all(
                (target / f"{s}.wav").is_file()
                and file_hash(target / f"{s}.wav") == manifest["sha256"].get(s)
                for s in SOURCES
            ):
                progress("Reusing separated vocals and instruments…")
                return {s: target / f"{s}.wav" for s in SOURCES}
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="separating-", dir=cache) as scratch:
            scratch = Path(scratch)
            progress("Separating vocals, drums, bass and instruments…")
            with open(scratch / "worker.log", "w", encoding="utf-8") as log:
                proc = subprocess.Popen(
                    command + [str(Path(path).resolve()), str(scratch), str(model_dir)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                last = ""
                try:
                    while proc.poll() is None:
                        check_cancel(cancel)
                        status = scratch / "progress.json"
                        if status.exists():
                            try:
                                message = json.loads(status.read_text(encoding="utf-8"))["message"]
                            except (OSError, ValueError, KeyError):
                                message = last
                            if message != last:
                                progress(message)
                                last = message
                        time.sleep(0.1)
                except BaseException:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    raise
            check_cancel(cancel)
            if proc.returncode:
                detail = (scratch / "worker.log").read_text(encoding="utf-8", errors="replace")[-1500:]
                raise MessageError("Audio separation failed. {detail}", detail=detail)
            hashes = {}
            for source in SOURCES:
                check_cancel(cancel)
                output = scratch / f"{source}.wav"
                with sf.SoundFile(output) as f:
                    if len(f) < f.samplerate or f.channels != 2:
                        raise MessageError("The separated {source} track is incomplete.", source=source)
                hashes[source] = file_hash(output)
            target.mkdir(exist_ok=True)
            # Publish the completion manifest last; interrupted jobs are never accepted as cache hits.
            for source in SOURCES:
                os.replace(scratch / f"{source}.wav", target / f"{source}.wav")
            temp_manifest = target / "manifest.tmp"
            temp_manifest.write_text(
                json.dumps(dict(sha256=hashes, model=model_fingerprint)), encoding="utf-8"
            )
            os.replace(temp_manifest, manifest_path)
            return {s: target / f"{s}.wav" for s in SOURCES}
