"""Capture generation requests and install only completed results."""

import copy
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from ...editing import replace_region
from ...models import LEVELS, Settings
from ...services import GenerationService
from ..dialogs import Dialogs
from ..workers import GenerationWorker

if TYPE_CHECKING:
    from ..window import Studio


class GenerationController(QObject):
    def __init__(self, window: "Studio"):
        super().__init__(window)
        self.window = window
        self.worker = None
        self.job_scope = None
        self.preserve_on_job = True
        self.service = GenerationService()

    def start_job(self, path, scope):
        window = self.window
        if self.worker:
            return
        try:
            settings = window.settings()
        except ValueError as ex:
            window.error(ex)
            return
        window.playback.player.pause()
        self.job_scope = scope
        self.preserve_on_job = window.view.preserve.isChecked()
        self.worker = GenerationWorker(self.service, path, settings, window)
        self.worker.progress.connect(window.show_status)
        self.worker.done.connect(self.generated)
        self.worker.failed.connect(window.error)
        self.worker.cancelled.connect(window.show_status)
        self.worker.finished.connect(self.job_finished)
        window.refresh_busy()
        self.worker.start()

    def cancel_generation(self):
        window = self.window
        if self.worker:
            self.worker.cancel()
            window.show_status("Cancelling… the previous project will be kept.")

    def job_finished(self):
        window = self.window
        old = self.worker
        self.worker = None
        if old:
            old.deleteLater()
        window.refresh_busy()

    def generated(self, project, audio):
        window = self.window
        if self.job_scope == "new":
            window.documents.install(project, audio)
            window.document.path = None
        else:
            window.editor.checkpoint()
            project["title"] = window.document.project["title"]
            project["audio_name"] = window.document.project["audio_name"]
            if isinstance(self.job_scope, tuple):
                start, end = self.job_scope
                level = window.view.level.currentData()
                project["maps"] = {
                    difficulty: replace_region(
                        window.document.project["maps"][difficulty],
                        project["maps"][difficulty],
                        start,
                        end,
                        self.preserve_on_job,
                    )
                    if difficulty == level
                    else copy.deepcopy(window.document.project["maps"][difficulty])
                    for difficulty in LEVELS
                }
            elif self.preserve_on_job:
                project["maps"] = {
                    difficulty: replace_region(
                        window.document.project["maps"][difficulty],
                        project["maps"][difficulty],
                        0,
                        project["analysis"]["duration_ms"],
                        True,
                    )
                    for difficulty in LEVELS
                }
            window.document.project = project
            window.view.timeline.set_analysis(project["analysis"])
            window.refresh()
        window.set_dirty()
        window.show_status("Map ready. You can preview it or export the selected difficulty.")
        window.documents.autosave()

    def regenerate(self):
        window = self.window
        if window.document.pending_audio and not self.worker:
            self.start_job(window.document.pending_audio, "new")
            return
        if not window.document.project or self.worker:
            return
        if not window.view.preserve.isChecked():
            if (
                Dialogs.question(
                    window,
                    "Regenerate",
                    "All three difficulties, including edits, will be replaced. Continue?",
                )
                != QMessageBox.Yes
            ):
                return
        self.start_job(window.playback.audio_path, "all")

    def regenerate_region(self):
        window = self.window
        if not window.document.project or self.worker:
            return
        start, end = window.playback.region()
        if end - start < 100:
            window.error("Select a range of at least 0.1 seconds.")
            return
        current = Settings.from_dict(window.document.project["settings"])
        try:
            requested = window.settings()
        except ValueError as exc:
            window.error(exc)
            return
        if (requested.bpm, requested.variable_tempo) != (current.bpm, current.variable_tempo):
            window.error(
                "To change the tempo, regenerate the entire map first. This keeps the unedited sections consistent."
            )
            return
        self.start_job(window.playback.audio_path, (start, end))
