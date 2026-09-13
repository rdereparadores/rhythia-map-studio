"""Snapshot policy shared by undo and asynchronous recovery saves."""

import copy

from .contracts import Project
from .immutable import freeze


def snapshot_project(project: Project) -> Project:
    snapshot = dict(project)
    snapshot["analysis"] = freeze(project["analysis"])
    snapshot["maps"] = copy.deepcopy(project["maps"])
    snapshot["settings"] = dict(project["settings"])
    return snapshot
