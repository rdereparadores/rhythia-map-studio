"""Undoable document edits, independent from the Qt widgets."""

import copy

from .quality import validate
from .snapshots import snapshot_project


class History:
    def __init__(self, limit=30):
        self.limit = limit
        self.past = []
        self.future = []

    def push(self, project):
        self.past.append(snapshot_project(project))
        self.past = self.past[-self.limit :]
        self.future.clear()

    def undo(self, current):
        if not self.past:
            return current
        self.future.append(current)
        return self.past.pop()

    def redo(self, current):
        if not self.future:
            return current
        self.past.append(current)
        return self.future.pop()


def move_notes(notes, indices, dx=0, dy=0, time_delta=0, duration=1200000):
    result = copy.deepcopy(notes)
    for index in indices:
        result[index]["X"] += dx
        result[index]["Y"] += dy
        result[index]["Time"] += int(time_delta)
        result[index]["Edited"] = True
    result.sort(key=lambda n: n["Time"])
    validate(result, duration, allow_empty=True)
    return result


def replace_region(existing, generated, start_ms, end_ms, preserve_edits=True):
    """Keep outside notes byte-for-byte, and avoid duplicate times near preserved edits."""
    kept = [
        dict(n)
        for n in existing
        if not start_ms <= n["Time"] < end_ms or (preserve_edits and n.get("Edited"))
    ]
    protected = [n["Time"] for n in kept if start_ms <= n["Time"] < end_ms]
    additions = [
        dict(n)
        for n in generated
        if start_ms <= n["Time"] < end_ms and all(abs(n["Time"] - t) >= 70 for t in protected)
    ]
    return sorted(kept + additions, key=lambda n: n["Time"])
