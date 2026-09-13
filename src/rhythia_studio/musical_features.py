"""Aligned stem descriptors and conservative melodic contour estimates.

Pitch is a soft geometry cue, not a transcription. Unvoiced/weak frames are gated.
All stem energies share the mixture reference to retain meaningful source balance.
"""

import math
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

from .messages import Message, MessageError
from .models import check_cancel

SOURCES = ("vocals", "drums", "bass", "other")


def describe_wave(mono, sr, target_times, reference_energy=None):
    divisor = math.gcd(sr, 22050)
    mono = signal.resample_poly(mono, 22050 // divisor, sr // divisor)
    freqs, times, z = signal.stft(mono, fs=22050, nperseg=2048, noverlap=1536)
    mag = np.abs(z)
    energy = np.sqrt(np.mean(mag * mag, axis=0))
    novelty = np.maximum(0, np.diff(np.log1p(100 * mag), axis=1, prepend=np.log1p(100 * mag[:, :1])))
    flux = novelty.mean(axis=0)
    flux = np.maximum(0, flux - signal.medfilt(flux, 9) * 0.6)
    flux /= max(float(np.quantile(flux, 0.98)), 1e-8)
    # Harmonic salience over a finite MIDI range is more stable than the brightest FFT bin.
    midi_candidates = np.arange(40, 85)
    f0 = 440 * 2 ** ((midi_candidates - 69) / 12)
    bins = np.rint(f0[:, None] * np.arange(1, 5)[None, :] / (22050 / 2048)).astype(int)
    salience = np.sum(mag[bins] / np.arange(1, 5)[None, :, None], axis=1)
    best = np.argmax(salience, axis=0)
    midi = signal.medfilt(midi_candidates[best].astype(float), 5)
    total = np.sum(mag[(freqs >= 65) & (freqs < 4000)], axis=0)
    confidence = np.clip(np.max(salience, axis=0) / np.maximum(total, 1e-8) * 2.5, 0, 1)
    silence_floor = max(float(np.quantile(energy, 0.95)) * 0.045, 1e-8)
    confidence[energy < silence_floor] = 0
    at = np.asarray(target_times) / 1000
    rms = np.interp(at, times, energy)
    ref = (
        np.asarray(reference_energy)
        if reference_energy is not None
        else np.full_like(rms, max(float(np.quantile(rms, 0.95)), 1e-8))
    )
    return dict(
        flux=np.round(np.minimum(2, np.interp(at, times, flux)), 4).tolist(),
        energy=np.round(rms / max(float(np.quantile(rms, 0.95)), 1e-8), 4).tolist(),
        relative_energy=np.round(np.clip(rms / np.maximum(ref, 1e-8), 0, 2), 4).tolist(),
        pitch=np.round(np.interp(at, times, midi), 3).tolist(),
        pitch_confidence=np.round(np.interp(at, times, confidence), 4).tolist(),
        raw_energy=rms,
    )


def attach_stems(analysis, paths, progress=lambda s: None, cancel=lambda: False):
    """Reject misaligned input, then attach features only (no stem paths in projects)."""
    descriptions = {}
    for source in SOURCES:
        check_cancel(cancel)
        progress(Message("Analyzing separated track: {source}…", source=source))
        with sf.SoundFile(Path(paths[source])) as f:
            duration_ms = len(f) / f.samplerate * 1000
            if abs(duration_ms - analysis["duration_ms"]) > 35:
                raise MessageError("The {source} track is not aligned with the song.", source=source)
            mono = f.read(dtype="float32", always_2d=True).mean(axis=1)
            descriptions[source] = describe_wave(mono, f.samplerate, analysis["times_ms"])
    # Shared scale avoids treating a quiet vocal leak as the dominant musical source.
    reference = np.sqrt(sum(np.asarray(d["raw_energy"]) ** 2 for d in descriptions.values()))
    for d in descriptions.values():
        raw = d.pop("raw_energy")
        d["relative_energy"] = np.round(np.clip(raw / np.maximum(reference, 1e-8), 0, 1), 4).tolist()
        d["pitch_confidence"] = np.round(
            np.asarray(d["pitch_confidence"]) * np.clip(raw / np.maximum(reference * 0.2, 1e-8), 0, 1), 4
        ).tolist()
    analysis["sources"] = descriptions
    analysis["separation"] = {"status": "ready", "model": "htdemucs", "sources": list(SOURCES)}
    return analysis
