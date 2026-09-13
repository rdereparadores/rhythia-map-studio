"""Musical tuning shared by generation and diagnostics.

These are heuristics, not official Rhythia difficulty ratings. Keep tuning
changes separate from structural refactors so output comparisons stay useful.
"""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class DifficultyProfile:
    subdivisions: int
    onset_threshold: float
    minimum_gap_ms: int
    maximum_speed: float  # Grid cells per second.
    strong_attack_threshold: float


PROFILES = MappingProxyType(
    {
        "Easy": DifficultyProfile(2, 0.39, 170, 10.0, 1.15),
        "Normal": DifficultyProfile(4, 0.25, 100, 17.0, 0.9),
        "Hard": DifficultyProfile(4, 0.13, 70, 25.0, 0.6),
    }
)


@dataclass(frozen=True)
class RhythmRules:
    minimum_energy: float = 0.07  # Relative to the source's 95th percentile.
    minimum_source_presence: float = 0.10  # Reject leaks from separated stems.
    pitch_confidence: float = 0.28
    pitch_lookback_ms: int = 100
    minimum_pitch_change: int = 1  # Semitones.
    maximum_pitch_change: int = 9
    breath_beats: float = 0.25  # Weak attacks can be omitted at phrase endings.
    breath_strong_attack: float = 0.9
    peak_distance_frames: int = 3
    peak_prominence: float = 0.09
    peak_height: float = 0.12
    beat_snap_ms: int = 65
    beat_snap_fraction: float = 0.43
    template_snap_ms: int = 30
    template_energy_floor: float = 0.06
    maximum_gap_density: float = 1.25


RHYTHM_RULES = RhythmRules()


@dataclass(frozen=True)
class PlannerRules:
    horizon: int = 8  # Notes considered together, not a repeating pattern length.
    beam_width: int = 14
    history_notes: int = 24
    anchor_weight: float = 9.0  # Preserve the identity of repeated sections.
    target_weight: float = 1.45
    distance_weight: float = 0.7
    fluid_turn_weight: float = 0.7
    jump_turn_weight: float = 0.25
    stationary_weight: float = 0.45
    short_repeat_penalty: float = 0.8
    long_repeat_penalty: float = 5.0
    stationary_repeat_penalty: float = 2.0


PLANNER_RULES = PlannerRules()
