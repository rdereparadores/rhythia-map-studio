"""Sequence self-similarity over half-beat chroma/timbre/onset descriptors.

Groups denote acoustic repetition, not a semantic claim that a region is a chorus.
Matching windows are non-overlapping; representatives are stable in song order.
"""

from collections import Counter

import numpy as np

from .models import check_cancel


def detect_sections(analysis, threshold=0.78, cancel=lambda: False):
    features = np.asarray(analysis.get("features", []), dtype=float)
    times = np.asarray(analysis.get("feature_times_ms", []), dtype=float)
    duration = analysis["duration_ms"]
    if len(features) < 32:
        return [dict(start_ms=0, end_ms=duration, group="U1", similarity=1.0, repeated=False)]
    # Center each channel across the track to reject generic timbral similarity.
    centered = (features - features.mean(axis=0)) / np.maximum(features.std(axis=0), 0.08)
    centered = np.clip(centered, -3, 3)
    centered[:, :12] *= 0.85
    centered[:, 12:18] *= 0.6
    centered[:, 18:] *= 1.1
    proposals = []
    for length in (64, 32):  # 8 or 4 bars in the provisional 4/4 grid.
        if len(features) < length * 2:
            continue
        starts = np.arange(0, len(features) - length + 1, 8)
        windows = np.array([centered[i : i + length].ravel() for i in starts])
        norms = np.linalg.norm(windows, axis=1)
        windows /= np.maximum(norms[:, None], 1e-8)
        scores = windows @ windows.T
        for row, start in enumerate(starts):
            check_cancel(cancel)
            for col in range(row + 1, len(starts)):
                other = starts[col]
                if other - start < length or norms[row] < 0.1 or norms[col] < 0.1:
                    continue
                similarity = float(scores[row, col])
                if similarity >= threshold:
                    proposals.append(
                        (similarity + 0.045 * (length / 32 - 1), similarity, int(start), int(other), length)
                    )
    owners = np.full(len(features), -1, dtype=int)
    groups = []
    for _, score, a, b, length in sorted(proposals, reverse=True):
        check_cancel(cancel)
        # Reuse a group only when the candidate aligns with a complete member window.
        matching = next(
            (g for g in groups if g["length"] == length and (a in g["starts"] or b in g["starts"])), None
        )
        if matching:
            new = b if a in matching["starts"] else a
            if np.all(owners[new : new + length] == -1):
                matching["starts"].append(new)
                matching["scores"][new] = score
                owners[new : new + length] = matching["id"]
        elif np.all(owners[a : a + length] == -1) and np.all(owners[b : b + length] == -1):
            ident = len(groups)
            groups.append(dict(id=ident, length=length, starts=[a, b], scores={a: 1.0, b: score}))
            owners[a : a + length] = ident
            owners[b : b + length] = ident
    groups.sort(key=lambda g: min(g["starts"]))
    sections = []
    for index, g in enumerate(groups):
        label = f"R{index + 1}"
        for start in sorted(g["starts"]):
            end = start + g["length"]
            sections.append(
                dict(
                    start_ms=round(float(times[start])),
                    end_ms=round(float(times[end])) if end < len(times) else duration,
                    group=label,
                    similarity=round(g["scores"][start], 3),
                    repeated=True,
                    feature_start=start,
                    feature_length=g["length"],
                )
            )
    # Fill uncovered regions with short phrases for generation and selective editing.
    cursor, unique = 0, 0
    result = []
    for section in sorted(sections, key=lambda s: s["start_ms"]) + [dict(start_ms=duration, end_ms=duration)]:
        while cursor < section["start_ms"]:
            unique += 1
            end = min(section["start_ms"], cursor + round(16 * 60000 / analysis["bpm"]))
            result.append(
                dict(start_ms=cursor, end_ms=end, group=f"U{unique}", similarity=1.0, repeated=False)
            )
            cursor = end
        if section["end_ms"] > section["start_ms"]:
            result.append(section)
            cursor = section["end_ms"]
    return result


def repetition_summary(sections):
    counts = Counter(s["group"] for s in sections if s["repeated"])
    return dict(
        groups=len(counts),
        occurrences=sum(counts.values()),
        repeated_ms=sum(s["end_ms"] - s["start_ms"] for s in sections if s["repeated"]),
    )
