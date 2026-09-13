"""Isolated Demucs worker. Uses only the explicit, hash-verified local model bundle."""

import hashlib
import json
import os
import sys
from pathlib import Path


def main():
    song, out, model_dir = map(Path, sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)

    def progress(message):
        temporary = out / "progress.tmp"
        temporary.write_text(json.dumps({"message": message}), encoding="utf-8")
        os.replace(temporary, out / "progress.json")

    progress("Loading the local separator…")
    import soundfile as sf
    import torch
    from demucs.apply import apply_model
    from demucs.audio import convert_audio
    from demucs.pretrained import get_model

    manifest = json.loads((model_dir / "manifest.json").read_text(encoding="utf-8"))
    for filename, digest in manifest["files"].items():
        data = (model_dir / filename).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("The local model does not match its hash: " + filename)
    torch.set_num_threads(min(8, os.cpu_count() or 4))
    torch.manual_seed(42)
    model = get_model(name="htdemucs", repo=model_dir)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    audio, sr = sf.read(song, dtype="float32", always_2d=True)
    wave = torch.from_numpy(audio.T.copy())
    wave = convert_audio(wave, sr, model.samplerate, model.audio_channels)
    reference = wave.mean(0)
    mean, std = reference.mean(), reference.std().clamp(min=1e-7)
    normalized = (wave - mean) / std
    progress("Separating all four tracks on " + ("GPU…" if device == "cuda" else "CPU…"))
    with torch.inference_mode():
        result = apply_model(
            model,
            normalized[None],
            device=device,
            shifts=0,
            split=True,
            overlap=0.25,
            progress=False,
            num_workers=0,
        )[0].cpu()
    result = result * std + mean / len(model.sources)
    progress("Saving tracks aligned with the original…")
    if result.shape[-1] != wave.shape[-1]:
        raise ValueError("The track duration does not match the audio.")
    for source, samples in zip(model.sources, result, strict=True):
        sf.write(out / (source + ".wav"), samples.numpy().T, model.samplerate, subtype="FLOAT")
    residual = torch.sqrt(torch.mean((result.sum(0) - wave) ** 2)).item()
    (out / "result.json").write_text(
        json.dumps(
            dict(device=device, sr=model.samplerate, frames=int(wave.shape[-1]), residual_rms=residual)
        ),
        encoding="utf-8",
    )
    progress("Separation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
