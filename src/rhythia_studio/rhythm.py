"""Choose musically justified note times before planning any grid positions."""

import numpy as np
from scipy.signal import find_peaks

from .arrangement import build_arrangement
from .models import DEFAULT_SETTINGS
from .profiles import PROFILES, RHYTHM_RULES


def source_curve(analysis, source, emphasis="Mix"):
    if source in analysis.get("sources", {}):
        return analysis["sources"][source]
    key = {"Mix": "flux", "Percussion": "percussion_flux", "Tonal": "tonal_flux", "Vocals": "tonal_flux"}[
        emphasis
    ]
    return dict(
        flux=analysis.get(key, analysis["flux"]),
        energy=analysis["energy"],
        relative_energy=np.ones(len(analysis["times_ms"])).tolist(),
        pitch=analysis.get("melody", {}).get("pitch", [60.0] * len(analysis["times_ms"])),
        pitch_confidence=analysis.get("melody", {}).get(
            "pitch_confidence", [0.0] * len(analysis["times_ms"])
        ),
    )


def thin_candidates(candidates, gap):
    kept = []
    for event in sorted(candidates, key=lambda e: e["time"]):
        if kept and event["time"] - kept[-1]["time"] < gap:
            if event["strength"] > kept[-1]["strength"]:
                kept[-1] = event
        else:
            kept.append(event)
    return kept


def add_candidate(candidates, analysis, times, curve, phrase, threshold, time, accent=0, require_peak=True):
    source = phrase["lead"]
    flux = curve["flux"]
    energy = float(np.interp(time, times, curve["energy"]))
    presence = float(np.interp(time, times, curve["relative_energy"]))
    if energy < RHYTHM_RULES.minimum_energy or (
        source != "mix" and presence < RHYTHM_RULES.minimum_source_presence
    ):
        return
    strength = float(np.interp(time, times, flux))
    pitch = float(np.interp(time, times, curve["pitch"]))
    confidence = float(np.interp(time, times, curve["pitch_confidence"]))
    previous_pitch = float(np.interp(time - RHYTHM_RULES.pitch_lookback_ms, times, curve["pitch"]))
    melodic_change = (
        source != "drums"
        and confidence > RHYTHM_RULES.pitch_confidence
        and RHYTHM_RULES.minimum_pitch_change
        <= abs(pitch - previous_pitch)
        <= RHYTHM_RULES.maximum_pitch_change
    )
    if strength < threshold and (require_peak or not melodic_change):
        return
    if (
        phrase["breath"]
        and time > phrase["end_ms"] - 60000 * RHYTHM_RULES.breath_beats / analysis["bpm"]
        and strength < RHYTHM_RULES.breath_strong_attack
    ):
        return
    if time < phrase["start_ms"] + 60000 / analysis["bpm"]:
        accent += phrase.get("impact", 0)
    candidates.append(
        dict(
            time=float(time),
            strength=strength + 0.2 * accent,
            accent=float(np.clip(strength / 1.4 + 0.25 * accent, 0, 1)),
            pitch=pitch,
            pitch_confidence=confidence,
            source=source,
            group=phrase["group"],
        )
    )


def rhythm(analysis, level, settings=DEFAULT_SETTINGS, source_data=None):
    profile = PROFILES[level]
    times = np.asarray(analysis["times_ms"])
    beats = np.asarray(analysis["beats_ms"])
    phrases = analysis.get("phrases") or build_arrangement(analysis, settings.emphasis)
    source_data = source_data or prepare_sources(analysis, phrases, settings.emphasis)
    candidates = []
    for phrase in phrases:
        source = phrase["lead"]
        curve, attacks = source_data[source]
        flux = np.asarray(curve["flux"])
        threshold = profile.onset_threshold * (1.35 - 0.6 * phrase["intensity"]) / settings.density

        for start, end in zip(beats, np.append(beats[1:], analysis["duration_ms"]), strict=True):
            if end <= phrase["start_ms"] or start >= phrase["end_ms"]:
                continue
            step = (end - start) / profile.subdivisions
            for subdivision in range(profile.subdivisions):
                t = start + subdivision * step
                if not phrase["start_ms"] <= t < phrase["end_ms"]:
                    continue
                index = np.searchsorted(attacks, t)
                near = attacks[max(0, index - 1) : min(len(attacks), index + 1)]
                nearest = float(near[np.argmin(abs(near - t))]) if len(near) else t
                close = abs(nearest - t) <= min(
                    RHYTHM_RULES.beat_snap_ms, RHYTHM_RULES.beat_snap_fraction * step
                )
                accent = subdivision == 0
                if close and phrase["start_ms"] <= nearest < phrase["end_ms"]:
                    add_candidate(candidates, analysis, times, curve, phrase, threshold, nearest, accent)
                elif accent:
                    add_candidate(
                        candidates, analysis, times, curve, phrase, threshold, t, accent, require_peak=False
                    )
        for attack in attacks:
            strong_threshold = profile.strong_attack_threshold
            if (
                phrase["start_ms"] <= attack < phrase["end_ms"]
                and np.interp(attack, times, flux) > strong_threshold / settings.density
            ):
                add_candidate(candidates, analysis, times, curve, phrase, threshold, attack)
    return thin_candidates(
        candidates, profile.minimum_gap_ms / min(RHYTHM_RULES.maximum_gap_density, settings.density)
    )


def prepare_sources(analysis, phrases, emphasis):
    """Compute attack arrays once per source for this generation request."""
    result = {}
    for phrase in phrases:
        source = phrase["lead"]
        if source in result:
            continue
        curve = source_curve(analysis, source, emphasis)
        peaks, _ = find_peaks(
            np.asarray(curve["flux"]),
            distance=RHYTHM_RULES.peak_distance_frames,
            prominence=RHYTHM_RULES.peak_prominence,
            height=RHYTHM_RULES.peak_height,
        )
        result[source] = (curve, np.asarray(analysis["times_ms"])[peaks])
    return result
