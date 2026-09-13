"""Shared domain settings and cancellation contract."""

import math
from dataclasses import asdict, dataclass
from typing import Callable

from .messages import MessageError

LEVELS = ("Easy", "Normal", "Hard")


class Cancelled(Exception):
    """A user cancellation, not an analysis failure."""


def check_cancel(cancel: Callable[[], bool]) -> None:
    if cancel():
        raise Cancelled("Operation cancelled; the previous project is kept.")


@dataclass(frozen=True)
class Settings:
    bpm: float = 0.0
    density: float = 1.0
    offset: int = 0
    seed: int = 42
    style: str = "Flowing"
    repeat_patterns: bool = True
    similarity: float = 0.78
    variable_tempo: bool = False
    emphasis: str = "Mix"
    separation: bool = False
    variation: float = 1.0

    def __post_init__(self):
        for name in ("bpm", "density", "offset", "seed", "similarity", "variation"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise MessageError("Invalid setting: {field}.", field=name)
        for name in ("seed", "offset"):
            if not isinstance(getattr(self, name), int):
                raise MessageError("Invalid setting: {field}.", field=name)
        for name in ("repeat_patterns", "variable_tempo", "separation"):
            if not isinstance(getattr(self, name), bool):
                raise MessageError("Invalid setting: {field}.", field=name)
        if self.bpm and not 35 <= self.bpm <= 300:
            raise ValueError("BPM must be 0 (automatic) or between 35 and 300.")
        if not 0.5 <= self.density <= 1.5 or not -2000 <= self.offset <= 2000:
            raise ValueError("Density or offset is out of range.")
        if not 0.5 <= self.similarity <= 0.98:
            raise ValueError("Similarity must be between 0.50 and 0.98.")
        if not 0.0 <= self.variation <= 2.0:
            raise ValueError("Variation must be between 0 and 2.")
        if self.style not in ("Flowing", "Jumps") or self.emphasis not in (
            "Mix",
            "Percussion",
            "Tonal",
            "Vocals",
        ):
            raise ValueError("Unknown generation profile.")
        if self.emphasis == "Vocals" and not self.separation:
            raise ValueError("Vocal priority requires instrument separation.")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        return cls(**{key: v for key, v in value.items() if key in cls.__dataclass_fields__})


DEFAULT_SETTINGS = Settings()
