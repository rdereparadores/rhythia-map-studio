"""Translate editor actions into validated, undoable document changes."""

import copy
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from ...editing import move_notes
from ...quality import validate

if TYPE_CHECKING:
    from ..window import Studio


class EditorController(QObject):
    def __init__(self, window: "Studio"):
        super().__init__(window)
        self.window = window

    def current_notes(self):
        window = self.window
        return window.document.project["maps"][window.view.level.currentData()]

    def selected_indices(self):
        window = self.window
        return sorted({item.row() for item in window.view.table.selectedItems()})

    def select_note(self):
        window = self.window
        indices = self.selected_indices()
        if not window.document.project or not indices:
            return
        index = indices[0]
        window.view.grid.selected = index
        window.view.note_time.setValue(self.current_notes()[index]["Time"] / 1000)
        window.playback.player.pause()
        window.playback.seek(self.current_notes()[index]["Time"])

    def select_section(self):
        window = self.window
        index = window.view.sections_table.currentRow()
        if not window.document.project or index < 0:
            return
        section = window.document.project["analysis"]["sections"][index]
        window.playback.player.pause()
        window.playback.set_region(section["start_ms"], section["end_ms"])
        window.playback.seek(section["start_ms"])
        window.view.timeline.start = section["start_ms"]
        window.view.timeline.span = max(1000, section["end_ms"] - section["start_ms"])
        window.view.timeline.update()

    def select_issue(self):
        window = self.window
        index = window.view.issues.currentRow()
        if 0 <= index < len(window.issues_data):
            window.playback.player.pause()
            window.playback.seek(window.issues_data[index]["time_ms"])

    def select_phrase(self):
        window = self.window
        index = window.view.phrases_table.currentRow()
        phrases = window.document.project["analysis"].get("phrases", []) if window.document.project else []
        if not 0 <= index < len(phrases):
            return
        phrase = phrases[index]
        window.playback.player.pause()
        window.playback.set_region(phrase["start_ms"], phrase["end_ms"])
        window.playback.seek(phrase["start_ms"])
        window.view.timeline.start = phrase["start_ms"]
        window.view.timeline.span = max(1000, phrase["end_ms"] - phrase["start_ms"])
        window.view.timeline.update()

    def checkpoint(self):
        window = self.window
        window.document.history.push(window.document.project)
        window.set_dirty()

    def commit_notes(self, notes):
        window = self.window
        if window.generation.worker:
            return
        validate(notes, window.document.project["analysis"]["duration_ms"], allow_empty=True)
        self.checkpoint()
        window.document.project["maps"][window.view.level.currentData()] = notes
        window.refresh()

    def move_note(self, x, y):
        window = self.window
        indices = self.selected_indices()
        if not window.document.project or not indices or window.generation.worker:
            return
        first = self.current_notes()[indices[0]]
        try:
            notes = move_notes(
                self.current_notes(),
                indices,
                dx=x - first["X"],
                dy=y - first["Y"],
                duration=window.document.project["analysis"]["duration_ms"],
            )
            self.commit_notes(notes)
        except ValueError as ex:
            window.error(ex)

    def retime(self):
        window = self.window
        indices = self.selected_indices()
        if not indices or window.generation.worker:
            return
        delta = round(window.view.note_time.value() * 1000) - self.current_notes()[indices[0]]["Time"]
        try:
            self.commit_notes(
                move_notes(
                    self.current_notes(),
                    indices,
                    time_delta=delta,
                    duration=window.document.project["analysis"]["duration_ms"],
                )
            )
        except ValueError as ex:
            window.error(ex)

    def drag_note(self, index, time):
        window = self.window
        if not window.document.project or window.generation.worker:
            return
        try:
            self.commit_notes(
                move_notes(
                    self.current_notes(),
                    [index],
                    time_delta=time - self.current_notes()[index]["Time"],
                    duration=window.document.project["analysis"]["duration_ms"],
                )
            )
        except ValueError as ex:
            window.error(ex)

    def add_note(self):
        window = self.window
        if not window.document.project or window.generation.worker:
            return
        notes = copy.deepcopy(self.current_notes())
        notes.append(dict(Time=window.playback.player.position(), X=1, Y=1, Edited=True, Section="Manual"))
        notes.sort(key=lambda n: n["Time"])
        try:
            self.commit_notes(notes)
        except ValueError as ex:
            window.error(ex)

    def delete_note(self):
        window = self.window
        indices = set(self.selected_indices())
        if window.document.project and indices and not window.generation.worker:
            self.commit_notes([dict(n) for i, n in enumerate(self.current_notes()) if i not in indices])

    def undo(self):
        window = self.window
        if window.document.project and window.document.history.past and not window.generation.worker:
            window.document.project = window.document.history.undo(window.document.project)
            self.restore_history()

    def redo(self):
        window = self.window
        if window.document.project and window.document.history.future and not window.generation.worker:
            window.document.project = window.document.history.redo(window.document.project)
            self.restore_history()

    def restore_history(self):
        window = self.window
        window.set_dirty()
        window.view.title_edit.setText(window.document.project["title"])
        window.apply_settings()
        window.view.timeline.set_analysis(window.document.project["analysis"])
        window.refresh()
