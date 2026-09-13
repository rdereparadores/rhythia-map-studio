"""JSON-compatible domain contracts. Times are milliseconds; pitch is MIDI.

Canonical field names and enum values are independent of the UI language.
TypedDict documents the wire format; project_validation enforces it at runtime.
"""

from typing import NotRequired, TypedDict

SCHEMA_VERSION = 1


class Note(TypedDict):
    Time: int
    X: float
    Y: float
    Edited: NotRequired[bool]
    Section: NotRequired[str]
    Source: NotRequired[str]
    Role: NotRequired[str]
    Accent: NotRequired[float]


class Section(TypedDict):
    start_ms: int
    end_ms: int
    group: str
    similarity: float
    repeated: bool
    feature_start: NotRequired[int]
    feature_length: NotRequired[int]


class Phrase(TypedDict):
    start_ms: int
    end_ms: int
    group: str
    part: int
    parts: int
    role: str
    energy: float
    lead_scores: dict[str, float]
    lead: str
    lead_label: str
    intensity: float
    impact: float
    breath: bool


class SourceFeatures(TypedDict):
    flux: list[float]
    energy: list[float]
    relative_energy: list[float]
    pitch: list[float]
    pitch_confidence: list[float]


class TimingPoint(TypedDict):
    OffsetMs: int
    Bpm: float


class Analysis(TypedDict):
    duration_ms: int
    audio_sha256: str
    bpm: float
    phase_ms: int
    times_ms: list[float]
    beats_ms: list[float]
    flux: list[float]
    energy: list[float]
    waveform: list[float]
    sections: list[Section]
    percussion_flux: NotRequired[list[float]]
    tonal_flux: NotRequired[list[float]]
    onsets_ms: NotRequired[list[float]]
    features: NotRequired[list[list[float]]]
    feature_times_ms: NotRequired[list[float]]
    analysis_version: NotRequired[int]
    phrases: NotRequired[list[Phrase]]
    sources: NotRequired[dict[str, SourceFeatures]]
    melody: NotRequired[dict[str, list[float]]]
    timing_points: NotRequired[list[TimingPoint]]
    separation: NotRequired[dict]
    estimated_bpm: NotRequired[float]
    tempo_confidence: NotRequired[float]
    tempo_mode: NotRequired[str]
    tempo_alternatives: NotRequired[list[float]]


class Project(TypedDict):
    version: int
    title: str
    audio_name: str
    settings: dict
    analysis: Analysis
    maps: dict[str, list[Note]]
