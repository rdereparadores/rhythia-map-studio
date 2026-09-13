"""Tempo/phase estimation and an optional, conservative local tempo tracker."""

import numpy as np
from scipy import signal

from .models import check_cancel


def estimate_timing(times_ms, flux, duration_ms, bpm=0, variable=False, cancel=lambda: False):
    times = np.asarray(times_ms) / 1000
    values = np.asarray(flux)
    fps = 1 / np.median(np.diff(times))
    ac = signal.correlate(values, values, mode="full", method="fft")[len(values) - 1 :]
    lags = np.arange(int(fps * 60 / 190), int(fps * 60 / 75) + 1)
    scores = ac[lags] * np.exp(-0.5 * (np.log2(60 * fps / lags / 125) / 0.9) ** 2)
    lag = int(lags[np.argmax(scores)])
    initial = 60 * fps / lag
    duration = duration_ms / 1000
    # Joint tempo/phase search over the whole song reduces cumulative drift.
    candidates = [float(bpm)] if bpm else np.linspace(initial * 0.975, initial * 1.025, 121)
    best = (-1.0, initial, 0.0)
    for tempo in candidates:
        check_cancel(cancel)
        period = 60 / tempo
        phases = np.arange(0, period, 1 / fps)
        beat_numbers = np.arange(int(duration / period))
        grid = phases[:, None] + beat_numbers[None, :] * period
        sampled = np.interp(grid.ravel(), times, values).reshape(grid.shape)
        # Clip isolated accents so one loud transient cannot select the tempo.
        alignment = np.minimum(sampled, 1.2).mean(axis=1)
        winner = int(np.argmax(alignment))
        if alignment[winner] > best[0]:
            best = (float(alignment[winner]), float(tempo), float(phases[winner]))
    _, tempo, phase = best
    tempo = round(tempo, 3)
    local = [(0.0, tempo)]
    if variable:
        for center in np.arange(8, duration, 8):
            check_cancel(cancel)
            sample = values[(times >= center - 8) & (times < center + 8)]
            if len(sample) < fps * 4 or np.max(sample) < 0.05:
                continue
            corr = signal.correlate(sample, sample, mode="full", method="fft")[len(sample) - 1 :]
            allowed = np.arange(max(2, int(fps * 60 / (tempo * 1.20))), int(fps * 60 / (tempo * 0.80)) + 1)
            allowed = allowed[allowed < len(corr)]
            prior = np.exp(-0.5 * (np.log((60 * fps / allowed) / local[-1][1]) / 0.12) ** 2)
            chosen = int(allowed[np.argmax(corr[allowed] * prior)])
            candidate = 60 * fps / chosen
            local.append((float(center), float(0.65 * local[-1][1] + 0.35 * candidate)))
    beats = []
    t = phase
    while t * 1000 < duration_ms:
        beats.append(round(t * 1000, 3))
        current = float(np.interp(t, [x[0] for x in local], [x[1] for x in local]))
        t += 60 / current
    timing_points = [dict(OffsetMs=round(beats[0]), Bpm=tempo)] if beats else []
    if variable:
        timing_points = [
            dict(OffsetMs=round(beats[i]), Bpm=round(60000 / (beats[i + 1] - beats[i]), 5))
            for i in range(len(beats) - 1)
        ]
    on_grid = np.interp(np.asarray(beats) / 1000, times, values) if beats else np.array([0])
    baseline = np.mean(values)
    confidence = float(np.clip((np.mean(on_grid) - baseline) / max(0.05, 1.2 - baseline), 0, 1))
    return dict(
        bpm=tempo,
        estimated_bpm=tempo,
        phase_ms=round(phase * 1000),
        beats_ms=beats,
        timing_points=timing_points,
        tempo_confidence=round(confidence, 3),
        tempo_mode="variable experimental" if variable else "constant",
        tempo_alternatives=[round(tempo / 2, 2), round(tempo * 2, 2)],
    )
