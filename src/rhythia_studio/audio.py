"""Audio decoding and compact spectral descriptors; no UI or file export logic."""

import hashlib
import io
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

from .models import DEFAULT_SETTINGS, check_cancel
from .musical_features import describe_wave
from .structure import detect_sections
from .timing import estimate_timing


def unit_rows(x):
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-8)


def analyze(path, settings=DEFAULT_SETTINGS, progress=lambda s: None, cancel=lambda: False):
    check_cancel(cancel)
    progress("Reading audio…")
    path = Path(path)
    if path.stat().st_size > 250_000_000:
        raise ValueError("The audio exceeds 250 MB.")
    raw = path.read_bytes()
    with sf.SoundFile(io.BytesIO(raw)) as f:
        duration = len(f) / f.samplerate
        if not 3 <= duration <= 1200:
            raise ValueError("Use audio between 3 seconds and 20 minutes long.")
        sr = f.samplerate
        # Decode in blocks; avoid retaining all original channels at high sample rates.
        chunks = []
        divisor = math.gcd(sr, 22050)
        while True:
            check_cancel(cancel)
            block = f.read(sr * 4, dtype="float32", always_2d=True)
            if not len(block):
                break
            chunks.append(signal.resample_poly(block.mean(axis=1), 22050 // divisor, sr // divisor))
    mono = np.concatenate(chunks)
    if not np.all(np.isfinite(mono)) or np.max(np.abs(mono)) < 1e-5:
        raise ValueError("The audio is empty, damaged or silent.")
    progress("Analyzing attacks, harmony and timbre…")
    check_cancel(cancel)
    # 2048-point frames improve pitch-class resolution for repeated-section matching.
    freqs, ts, z = signal.stft(mono, fs=22050, nperseg=2048, noverlap=1536)
    mag = np.abs(z).astype("float32")
    del z
    logmag = np.log1p(100 * mag)
    novelty = np.maximum(0, np.diff(logmag, axis=1, prepend=logmag[:, :1]))

    def onset_curve(mask):
        curve = novelty[mask].mean(axis=0)
        curve = np.maximum(0, curve - signal.medfilt(curve, 9) * 0.65)
        return np.minimum(2.0, curve / max(float(np.quantile(curve, 0.98)), 1e-8))

    flux = onset_curve(freqs >= 30)
    percussion = onset_curve((freqs >= 1800) | (freqs <= 160))
    tonal = onset_curve((freqs > 160) & (freqs < 1800))
    energy = np.sqrt(np.mean(mag**2, axis=0))
    energy /= max(float(np.quantile(energy, 0.95)), 1e-8)
    chroma = np.zeros((len(ts), 12), dtype="float32")
    selected = np.where((freqs >= 65) & (freqs <= 3000))[0]
    pitch = np.round(69 + 12 * np.log2(freqs[selected] / 440)).astype(int) % 12
    for pc in range(12):
        chroma[:, pc] = mag[selected[pitch == pc]].sum(axis=0)
    chroma = unit_rows(chroma)
    bands = np.array(
        [
            np.log1p(100 * mag[(freqs >= lo) & (freqs < hi)].mean(axis=0))
            for lo, hi in zip(
                [30, 120, 300, 700, 1500, 3500], [120, 300, 700, 1500, 3500, 10000], strict=True
            )
        ]
    ).T
    bands = unit_rows(bands)
    peaks, _ = signal.find_peaks(flux, distance=3, prominence=0.09, height=0.12)
    times_ms = ts * 1000
    progress("Refining tempo and phase throughout the song…")
    timing = estimate_timing(
        times_ms, flux, round(duration * 1000), settings.bpm, settings.variable_tempo, cancel
    )
    # Half-beat descriptors retain rhythmic sequence, not only average song timbre.
    beats = np.array(timing["beats_ms"])
    halfbeats = np.sort(np.concatenate((beats, (beats[:-1] + beats[1:]) / 2)))
    features = []
    for start, end in zip(halfbeats, np.append(halfbeats[1:], duration * 1000), strict=True):
        mask = (times_ms >= start) & (times_ms < end)
        if not np.any(mask):
            mask[np.argmin(np.abs(times_ms - start))] = True
        features.append(
            np.concatenate(
                (
                    chroma[mask].mean(axis=0),
                    bands[mask].mean(axis=0),
                    [flux[mask].max(), np.mean(energy[mask])],
                )
            )
        )
    analysis = dict(
        duration_ms=round(duration * 1000),
        times_ms=np.round(times_ms, 2).tolist(),
        flux=np.round(flux, 4).tolist(),
        percussion_flux=np.round(percussion, 4).tolist(),
        tonal_flux=np.round(tonal, 4).tolist(),
        energy=np.round(energy, 4).tolist(),
        onsets_ms=np.round(times_ms[peaks]).astype(int).tolist(),
        waveform=[round(float(np.max(np.abs(c))), 4) if len(c) else 0 for c in np.array_split(mono, 2400)],
        features=np.round(features, 5).tolist(),
        feature_times_ms=halfbeats.tolist(),
        audio_sha256=hashlib.sha256(raw).hexdigest(),
        analysis_version=3,
        **timing,
    )
    progress("Comparing phrases to find repeated sections…")
    analysis["sections"] = detect_sections(analysis, settings.similarity, cancel)
    melody = describe_wave(mono, 22050, analysis["times_ms"])
    analysis["melody"] = {key: melody[key] for key in ("pitch", "pitch_confidence")}
    analysis["separation"] = {"status": "disabled"}
    check_cancel(cancel)
    return analysis
