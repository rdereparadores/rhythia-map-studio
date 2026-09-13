"""Descriptive playability diagnostics; never presented as official star ratings."""

import math

import numpy as np

from .messages import Message
from .profiles import PROFILES


def validate(notes, duration, allow_empty=False):
    if not notes and not allow_empty:
        raise ValueError("The map has no notes.")
    last = -1
    for n in notes:
        t, x, y = n["Time"], n["X"], n["Y"]
        if not all(math.isfinite(float(v)) for v in (t, x, y)):
            raise ValueError("A note contains non-finite values.")
        if int(t) != t or t <= last or not 0 <= t < duration or not 0 <= x <= 2 or not 0 <= y <= 2:
            raise ValueError("Check for duplicate times, note order and positions.")
        last = t


def evaluate(notes, duration, level):
    if not notes:
        return dict(notes=0, nps=0, peak_nps=0, p95_speed=0, rest_pct=100, warnings=[])
    a = np.array([[n["Time"], n["X"], n["Y"]] for n in notes], dtype=float)
    dt = np.diff(a[:, 0]) / 1000
    steps = np.diff(a[:, 1:], axis=0)
    speed = np.linalg.norm(steps, axis=1) / np.maximum(dt, 0.001)
    right = np.searchsorted(a[:, 0], a[:, 0] + 1000, side="left")
    peak = int(np.max(right - np.arange(len(a))))
    warnings = []
    for i, v in enumerate(speed):
        if v > PROFILES[level].maximum_speed + 1e-6:
            warnings.append(
                dict(
                    index=i + 1,
                    time_ms=int(a[i + 1, 0]),
                    message=Message("Fast jump: {speed} cells/s", speed=f"{v:.1f}"),
                )
            )
    for i, (u, v) in enumerate(zip(steps, steps[1:], strict=False)):
        if dt[i + 1] < 0.16 and np.dot(u, v) < -1:
            warnings.append(dict(index=i + 2, time_ms=int(a[i + 2, 0]), message="Sharp direction change"))
    density = len(notes) / (duration / 1000)
    p95 = float(np.quantile(speed, 0.95)) if len(speed) else 0
    return dict(
        notes=len(notes),
        nps=round(density, 2),
        peak_nps=peak,
        p95_speed=round(p95, 2),
        rest_pct=round(float(np.sum(dt[dt > 1])) / (duration / 1000) * 100, 1),
        warnings=warnings,
        effort_index=round(0.5 * density + 0.16 * p95 + 0.1 * peak, 2),
    )
