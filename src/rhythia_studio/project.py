"""Versioned portable projects, recovery snapshots and atomic RHM export."""

import hashlib
import json
import os
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

from .contracts import SCHEMA_VERSION as SCHEMA_VERSION
from .contracts import Project
from .immutable import freeze
from .messages import MessageError
from .models import LEVELS, Settings
from .project_validation import validate_project
from .quality import validate


def atomic_zip(path, entries):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(fd)
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as z:
            for name, value in entries.items():
                z.writestr(name, value)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def save_project(path: str | Path, project: Project, audio: bytes) -> None:
    validate_project(project)
    for notes in project["maps"].values():
        validate(notes, project["analysis"]["duration_ms"], allow_empty=True)
    if hashlib.sha256(audio).hexdigest() != project["analysis"]["audio_sha256"]:
        raise ValueError("The audio does not match the project.")
    atomic_zip(
        path,
        {"project.json": json.dumps(project, ensure_ascii=False, allow_nan=False).encode(), "audio": audio},
    )


def load_project(path: str | Path) -> tuple[Project, bytes]:
    with zipfile.ZipFile(path) as z:
        if z.getinfo("project.json").file_size > 40_000_000 or z.getinfo("audio").file_size > 250_000_000:
            raise ValueError("The project exceeds the size limit.")
        p, audio = json.loads(z.read("project.json")), z.read("audio")
    if not isinstance(p, dict):
        raise MessageError("Invalid project field: {field}.", field="project")
    if type(p.get("version")) is not int or p["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported project version.")
    validate_project(p)
    p["settings"] = Settings.from_dict(p["settings"]).to_dict()
    if hashlib.sha256(audio).hexdigest() != p["analysis"]["audio_sha256"]:
        raise ValueError("The audio does not match the project's fingerprint.")
    p["analysis"] = freeze(p["analysis"])
    return p, audio


def cover_png():
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    rows = []
    for y in range(256):
        row = bytearray([0])
        for x in range(256):
            square = 35 <= x < 221 and 35 <= y < 221 and (x - 35) % 66 < 54 and (y - 35) % 66 < 54
            row.extend((95, 220, 191) if square else (13, 21 + int(y / 20), 35 + int(x / 15)))
        rows.append(bytes(row))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


def export_rhm(path: str | Path, project: Project, level: str, audio: bytes) -> None:
    a = project["analysis"]
    validate(project["maps"][level], a["duration_ms"])
    if hashlib.sha256(audio).hexdigest() != a["audio_sha256"]:
        raise ValueError("The audio does not match the map.")
    notes = [{key: n[key] for key in ("Time", "X", "Y")} for n in project["maps"][level]]
    ident = hashlib.sha256((a["audio_sha256"] + level + json.dumps(notes)).encode()).hexdigest()[:16]
    offset = project["settings"].get("offset", 0)
    timing = a.get("timing_points", [dict(OffsetMs=a["phase_ms"], Bpm=a["bpm"])])
    shifted = [dict(OffsetMs=max(0, round(p["OffsetMs"] + offset)), Bpm=p["Bpm"]) for p in timing]
    # A negative offset can collapse early timing points at zero.
    shifted = list({p["OffsetMs"]: p for p in shifted if p["OffsetMs"] < a["duration_ms"]}.values())
    data = dict(
        OnlineId=None,
        OnlineStatus=None,
        LegacyId=ident,
        SongName=project["title"],
        Mappers=["Rhythia Map Studio"],
        Title=project["title"] + " — " + level,
        Duration=a["duration_ms"],
        Difficulty=LEVELS.index(level) + 1,
        CustomDifficultyName=level + " (generated)",
        StarRating=0,
        Notes=notes,
        AudioFileName=Path(project["audio_name"]).name,
        ImagePath="cover",
        TimingPoints=shifted,
    )
    atomic_zip(
        path,
        {
            "map": json.dumps(data, ensure_ascii=False, allow_nan=False).encode(),
            "audio": audio,
            "cover": cover_png(),
        },
    )


class RecoveryStore:
    def __init__(self, directory):
        self.directory = Path(directory)

    def path_for(self, project):
        return self.directory / (project["analysis"]["audio_sha256"][:16] + ".rmapproj")

    def save(self, project, audio):
        save_project(self.path_for(project), project, audio)

    def snapshots(self):
        return sorted(self.directory.glob("*.rmapproj"), key=lambda p: p.stat().st_mtime, reverse=True)

    def discard(self, project):
        self.path_for(project).unlink(missing_ok=True)
