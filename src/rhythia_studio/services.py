"""Application use cases. Owns caching; never imports Qt."""

import hashlib
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Protocol

from .arrangement import build_arrangement
from .audio import analyze
from .contracts import SCHEMA_VERSION, Project
from .generation import generate_maps
from .immutable import freeze
from .models import DEFAULT_SETTINGS, Settings, check_cancel
from .musical_features import attach_stems
from .project_validation import validate_project
from .separation import SeparationEngine
from .structure import detect_sections


class Separator(Protocol):
    def separate(
        self, path: Path, progress: Callable[[str], None], cancel: Callable[[], bool]
    ) -> dict[str, Path]: ...


class GenerationService:
    def __init__(self, separator: Separator | None = None):
        self.cache = OrderedDict()
        self.separator = separator

    def create(
        self,
        path: str | Path,
        settings: Settings = DEFAULT_SETTINGS,
        progress: Callable[[str], None] = lambda message: None,
        cancel: Callable[[], bool] = lambda: False,
    ) -> tuple[Project, bytes]:
        check_cancel(cancel)
        path = Path(path)
        if path.stat().st_size > 250_000_000:
            raise ValueError("The file exceeds 250 MB.")
        audio = path.read_bytes()
        digest = hashlib.sha256(audio).hexdigest()
        key = (digest, settings.bpm, settings.variable_tempo, settings.separation)
        if key in self.cache:
            progress("Reusing audio analysis…")
            analysis = dict(self.cache[key])
            analysis["sections"] = detect_sections(analysis, settings.similarity, cancel)
        else:
            analysis = analyze(path, settings, progress, cancel)
            if settings.separation:
                separator = self.separator or SeparationEngine()
                paths = separator.separate(path, progress, cancel)
                analysis = attach_stems(analysis, paths, progress, cancel)
            self.cache[key] = freeze(analysis)
            while len(self.cache) > 3:
                self.cache.popitem(last=False)
        analysis = dict(analysis)
        analysis["phrases"] = build_arrangement(analysis, settings.emphasis)
        progress("Planning phrases, accents and upcoming movements…")
        maps = generate_maps(analysis, settings, cancel)
        check_cancel(cancel)
        project: Project = dict(
            version=SCHEMA_VERSION,
            title=path.stem,
            audio_name=path.name,
            analysis=freeze(analysis),
            settings=settings.to_dict(),
            maps=maps,
        )
        validate_project(project)
        return project, audio
