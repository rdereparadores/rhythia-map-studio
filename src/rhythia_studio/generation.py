"""Phrase-aware rhythm selection, reusable arrangements and planned trajectories."""

import numpy as np

from .arrangement import build_arrangement
from .contracts import Analysis, Note
from .models import DEFAULT_SETTINGS, LEVELS, check_cancel
from .planner import movement_intents, plan_positions, stable_seed
from .profiles import PROFILES, RHYTHM_RULES
from .rhythm import add_candidate as add_candidate
from .rhythm import prepare_sources, thin_candidates
from .rhythm import rhythm as rhythm


def generate(analysis: Analysis, level: str, settings=DEFAULT_SETTINGS, cancel=lambda: False) -> list[Note]:
    profile = PROFILES[level]
    phrases = analysis.get("phrases") or build_arrangement(analysis, settings.emphasis)
    cache = {}
    timeline = []
    source_data = prepare_sources(analysis, phrases, settings.emphasis)
    events = rhythm(analysis, level, settings, source_data)
    for section_index, section in enumerate(analysis["sections"]):
        check_cancel(cancel)
        group = section["group"] if settings.repeat_patterns else f"phrase-{section_index}"
        if group not in cache:
            cache[group] = plan_section(events, phrases, section, group, profile, settings, cancel)
        timeline.extend(adapt_template(analysis, section, phrases, cache[group], source_data, settings))
    timeline = thin_candidates(
        timeline, profile.minimum_gap_ms / min(RHYTHM_RULES.maximum_gap_density, settings.density)
    )
    result = plan_positions(timeline, profile.maximum_speed, settings.style, settings.variation, cancel)
    return [
        dict(
            Time=event["time"],
            X=event["X"],
            Y=event["Y"],
            Section=event["group"],
            Edited=False,
            Source=event["source"],
            Role=event["role"],
            Accent=round(event["accent"], 3),
        )
        for event in result
    ]


def generate_maps(analysis, settings, cancel=lambda: False):
    return {level: generate(analysis, level, settings, cancel) for level in LEVELS}


def plan_section(events, phrases, section, group, profile, settings, cancel):
    """Plan one canonical occurrence; repetitions reuse its relative timing."""
    start, end = section["start_ms"], section["end_ms"]
    intents = []
    local_phrases = [phrase for phrase in phrases if start <= phrase["start_ms"] < end]
    for phrase in local_phrases:
        local = [event for event in events if phrase["start_ms"] <= event["time"] < phrase["end_ms"]]
        intents.extend(
            movement_intents(local, phrase, stable_seed(settings.seed, group + "/" + str(phrase["part"])))
        )
    planned = plan_positions(intents, profile.maximum_speed, settings.style, settings.variation, cancel)
    return end - start, [dict(event, relative_ms=event["time"] - start) for event in planned]


def adapt_template(analysis, section, phrases, cached, source_data, settings):
    """Fit a canonical pattern to local duration, attacks, silence and offset."""
    start, end = section["start_ms"], section["end_ms"]
    reference_duration, template = cached
    result = []
    ratio = (end - start) / max(1, reference_duration)
    for event in template:
        time_ms = start + event["relative_ms"] * ratio
        phrase = next(
            (phrase for phrase in phrases if phrase["start_ms"] <= time_ms < phrase["end_ms"]), None
        )
        if phrase is None:
            continue
        curve, attacks = source_data[phrase["lead"]]
        attack_index = np.searchsorted(attacks, time_ms)
        near = attacks[max(0, attack_index - 1) : min(len(attacks), attack_index + 1)]
        if len(near):
            nearest = float(near[np.argmin(abs(near - time_ms))])
            if abs(nearest - time_ms) <= RHYTHM_RULES.template_snap_ms and start <= nearest < end:
                time_ms = nearest
        if np.interp(time_ms, analysis["times_ms"], curve["energy"]) < RHYTHM_RULES.template_energy_floor:
            continue
        shifted = round(time_ms + settings.offset)
        if not 0 <= shifted < analysis["duration_ms"]:
            continue
        result.append(
            dict(
                event,
                time=shifted,
                target=(event["X"], event["Y"]),
                anchor=True,
                source=phrase["lead"],
                group=section["group"],
                pitch=float(np.interp(time_ms, analysis["times_ms"], curve["pitch"])),
                pitch_confidence=float(np.interp(time_ms, analysis["times_ms"], curve["pitch_confidence"])),
            )
        )
    return result
