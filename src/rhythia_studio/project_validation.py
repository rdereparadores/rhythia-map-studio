"""Validate project boundaries before any UI or algorithm consumes their data."""

import math
import re

from .contracts import SCHEMA_VERSION, Project
from .messages import MessageError
from .models import LEVELS, Settings
from .quality import validate as validate_notes


def _require(condition, field):
    if not condition:
        raise MessageError("Invalid project field: {field}.", field=field)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _array(value, field, length=None, nonempty=False):
    _require(isinstance(value, (list, tuple)), field)
    _require(not nonempty or bool(value), field)
    _require(length is None or len(value) == length, field)
    _require(all(_number(item) for item in value), field)
    return value


def _times(value, field, duration=None):
    values = _array(value, field, nonempty=True)
    _require(values[0] >= 0 and all(a < b for a, b in zip(values, values[1:], strict=False)), field)
    if duration is not None:
        _require(values[-1] < duration, field)
    return values


def _intervals(items, field, duration):
    _require(isinstance(items, (list, tuple)), field)
    previous_end = 0
    for index, item in enumerate(items):
        name = f"{field}[{index}]"
        _require(isinstance(item, dict), name)
        start, end = item.get("start_ms"), item.get("end_ms")
        _require(_number(start) and _number(end), name)
        _require(previous_end <= start < end <= duration, name)
        _require(isinstance(item.get("group"), str), name + ".group")
        previous_end = end


def validate_project(project: Project) -> None:
    """Validate the current project format.

    Unknown fields are retained for forwards compatibility. Known arrays must
    align with their time axis; diagnostics identify the offending field.
    """
    _require(isinstance(project, dict), "project")
    _require(type(project.get("version")) is int and project["version"] == SCHEMA_VERSION, "version")
    for key in ("title", "audio_name"):
        _require(isinstance(project.get(key), str), key)
    _require(isinstance(project.get("settings"), dict), "settings")
    Settings.from_dict(project["settings"])
    analysis = project.get("analysis")
    _require(isinstance(analysis, dict), "analysis")
    duration = analysis.get("duration_ms")
    _require(isinstance(duration, int) and not isinstance(duration, bool) and duration > 0, "duration_ms")
    digest = analysis.get("audio_sha256")
    _require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), "audio_sha256")
    _require(_number(analysis.get("bpm")) and analysis["bpm"] > 0, "bpm")
    _require(_number(analysis.get("phase_ms")), "phase_ms")
    frames = _times(analysis.get("times_ms"), "times_ms")
    _times(analysis.get("beats_ms"), "beats_ms", duration)
    for key in ("flux", "energy"):
        _array(analysis.get(key), key, len(frames))
    for key in ("percussion_flux", "tonal_flux"):
        if key in analysis:
            _array(analysis[key], key, len(frames))
    _array(analysis.get("waveform"), "waveform", nonempty=True)
    if "features" in analysis or "feature_times_ms" in analysis:
        times = _times(analysis.get("feature_times_ms"), "feature_times_ms")
        features = analysis.get("features")
        _require(isinstance(features, (list, tuple)) and len(features) == len(times), "features")
        width = len(_array(features[0], "features[0]", nonempty=True))
        for row in features:
            _array(row, "features", width)
    sources = analysis.get("sources", {})
    _require(isinstance(sources, dict), "sources")
    for source, features in sources.items():
        _require(source in ("vocals", "drums", "bass", "other"), "sources")
        _require(isinstance(features, dict), f"sources.{source}")
        for key in ("flux", "energy", "relative_energy", "pitch", "pitch_confidence"):
            _array(features.get(key), f"sources.{source}.{key}", len(frames))
    if "melody" in analysis:
        _require(isinstance(analysis["melody"], dict), "melody")
        for key in ("pitch", "pitch_confidence"):
            _array(analysis["melody"].get(key), f"melody.{key}", len(frames))
    sections = analysis.get("sections")
    _intervals(sections, "sections", duration)
    _require(bool(sections), "sections")
    for section in sections:
        _require(isinstance(section.get("repeated"), bool), "sections.repeated")
        similarity = section.get("similarity")
        _require(_number(similarity) and 0 <= similarity <= 1, "sections.similarity")
    phrases = analysis.get("phrases", [])
    _intervals(phrases, "phrases", duration)
    groups = {section["group"] for section in sections}
    for phrase in phrases:
        _require(phrase["group"] in groups, "phrases.group")
        for key in ("intensity", "impact", "energy"):
            _require(_number(phrase.get(key)), f"phrases.{key}")
        _require(0 <= phrase["intensity"] <= 1, "phrases.intensity")
        for key in ("part", "parts"):
            _require(isinstance(phrase.get(key), int), f"phrases.{key}")
        _require(0 <= phrase["part"] < phrase["parts"], "phrases.part")
        _require(phrase.get("lead") in {"mix", *sources}, "phrases.lead")
        _require(isinstance(phrase.get("lead_label"), str), "phrases.lead_label")
        _require(phrase.get("role") in ("intro", "development", "ending"), "phrases.role")
        _require(isinstance(phrase.get("breath"), bool), "phrases.breath")
    points = analysis.get("timing_points", [])
    _require(isinstance(points, (list, tuple)), "timing_points")
    previous_offset = -1
    for point in points:
        _require(isinstance(point, dict), "timing_points")
        offset, bpm = point.get("OffsetMs"), point.get("Bpm")
        _require(_number(offset) and previous_offset <= offset < duration, "timing_points.OffsetMs")
        _require(_number(bpm) and bpm > 0, "timing_points.Bpm")
        previous_offset = offset
    maps = project.get("maps")
    _require(isinstance(maps, dict), "maps")
    for level in LEVELS:
        notes = maps.get(level)
        _require(isinstance(notes, list), f"maps.{level}")
        for note in notes:
            _require(isinstance(note, dict), f"maps.{level}.note")
            for key in ("Time", "X", "Y"):
                _require(_number(note.get(key)), f"maps.{level}.{key}")
            for key in ("Section", "Source", "Role"):
                if key in note:
                    _require(isinstance(note[key], str), f"maps.{level}.{key}")
            if "Edited" in note:
                _require(isinstance(note["Edited"], bool), f"maps.{level}.Edited")
            if "Accent" in note:
                _require(_number(note["Accent"]) and 0 <= note["Accent"] <= 1, f"maps.{level}.Accent")
        validate_notes(notes, duration, allow_empty=True)
