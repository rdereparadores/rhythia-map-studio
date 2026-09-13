"""Editable document state and isolated snapshots, independent of Qt.

Analysis is recursively frozen at the service/load boundaries. Snapshots share
that large read-only payload; editable maps and settings are copied explicitly.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .contracts import Project
from .editing import History


@dataclass
class DocumentSession:
    project: Project | None = None
    audio: bytes | None = None
    path: str | None = None
    dirty: bool = False
    pending_audio: Path | None = None
    history: History = field(default_factory=History)
