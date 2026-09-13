"""Open, save, recover and install documents; owns recovery jobs."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from ...editing import History
from ...messages import Message
from ...project import RecoveryStore, export_rhm, load_project, save_project
from ...snapshots import snapshot_project
from ..dialogs import Dialogs
from ..workers import SaveWorker

if TYPE_CHECKING:
    from ..window import Studio


class DocumentController(QObject):
    def __init__(self, window: "Studio", recovery_directory):
        super().__init__(window)
        self.window = window
        self.save_worker = None
        self.recovery = RecoveryStore(recovery_directory)

    def confirm_discard(self):
        window = self.window
        if not window.document.dirty:
            return True
        choice = Dialogs.question(
            window,
            "Unsaved changes",
            "Save the project before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if choice == QMessageBox.Save:
            return self.save()
        if choice == QMessageBox.Discard:
            self.recovery.discard(window.document.project)
            return True
        return False

    def import_audio(self):
        window = self.window
        if window.generation.worker or not self.confirm_discard():
            return
        path, _ = Dialogs.getOpenFileName(
            window, "Choose song", str(Path.home() / "Documents"), "Audio (*.mp3 *.wav *.flac *.ogg)"
        )
        if path:
            self.choose_audio(path)

    def choose_audio(self, path):
        """Stage a song so the user can choose priorities before starting analysis."""
        window = self.window
        window.playback.player.stop()
        window.document.pending_audio = Path(path)
        window.view.bpm.setValue(0)
        window.view.song.setText(window.document.pending_audio.name)
        window.refresh()

    def install(self, project, audio):
        window = self.window
        window.playback.load_audio(project["audio_name"], audio)
        window.document.pending_audio = None
        window.document.project, window.document.audio = project, audio
        window.view.song.setText(project["audio_name"])
        window.view.title_edit.setText(project["title"])
        window.apply_settings()
        window.document.history = History()
        window.view.slider.setRange(0, project["analysis"]["duration_ms"])
        window.view.note_time.setMaximum((project["analysis"]["duration_ms"] - 1) / 1000)
        for control in (window.view.range_start, window.view.range_end):
            control.setMaximum(project["analysis"]["duration_ms"] / 1000)
        window.view.timeline.set_analysis(project["analysis"])
        window.playback.set_region(0, min(10000, project["analysis"]["duration_ms"]))
        window.set_dirty(False)
        window.refresh()
        window.playback.position(0)

    def change_title(self, text):
        window = self.window
        if window.document.project:
            window.document.project["title"] = text
            window.view.preview_title.setText(text)
            window.set_dirty()

    def save(self):
        window = self.window
        if not window.document.project or window.generation.worker:
            return False
        path = window.document.path
        if not path:
            path, _ = Dialogs.getSaveFileName(
                window, "Save project", "My map.rmapproj", "Project (*.rmapproj)"
            )
        if not path:
            return False
        if not str(path).lower().endswith(".rmapproj"):
            path = str(path) + ".rmapproj"
        try:
            save_project(path, window.document.project, window.document.audio)
            window.document.path = str(path)
            window.set_dirty(False)
            self.recovery.discard(window.document.project)
            window.show_status(Message("Project saved: {detail}", detail=str(path)))
            return True
        except Exception as ex:
            logging.getLogger(__name__).exception("Document operation failed")
            window.error(ex)
            return False

    def open_project(self):
        window = self.window
        if window.generation.worker or not self.confirm_discard():
            return
        path, _ = Dialogs.getOpenFileName(window, "Open project", "", "Project (*.rmapproj)")
        if path:
            self.read_project(path)

    def read_project(self, path):
        window = self.window
        try:
            project, audio = load_project(path)
            self.install(project, audio)
            window.document.path = str(path)
            window.show_status("Project opened.")
        except Exception as ex:
            logging.getLogger(__name__).exception("Document operation failed")
            window.error(ex)

    def export(self):
        window = self.window
        if not window.document.project or window.generation.worker:
            return
        level = window.view.level.currentData()
        path, _ = Dialogs.getSaveFileName(
            window,
            "Export selected difficulty",
            Message("My map - {level}.rhm", level=window.t(level)),
            "Rhythia map (*.rhm)",
        )
        if not path:
            return
        if not path.lower().endswith(".rhm"):
            path += ".rhm"
        try:
            export_rhm(path, window.document.project, level, window.document.audio)
            window.show_status(
                Message("Exported. In Rhythia Steam: Settings → Import Files. {detail}", detail=path)
            )
        except Exception as ex:
            logging.getLogger(__name__).exception("Document operation failed")
            window.error(ex)

    def autosave(self):
        window = self.window
        if not window.document.project or not window.document.dirty or self.save_worker:
            return
        snapshot = snapshot_project(window.document.project)
        self.save_worker = SaveWorker(self.recovery, snapshot, window.document.audio, window)
        self.save_worker.failed.connect(
            lambda error: window.show_status(Message("Autosave failed: {detail}", detail=error))
        )
        self.save_worker.finished.connect(self.autosave_finished)
        self.save_worker.start()

    def autosave_finished(self):
        window = self.window
        old = self.save_worker
        self.save_worker = None
        if old:
            if (
                window.document.project
                and not window.document.dirty
                and old.project["analysis"]["audio_sha256"]
                == window.document.project["analysis"]["audio_sha256"]
            ):
                self.recovery.discard(old.project)
            old.deleteLater()

    def offer_recovery(self):
        window = self.window
        if (
            Dialogs.question(
                window, "Recovery available", "Autosaved projects are available. Would you like to open one?"
            )
            == QMessageBox.Yes
        ):
            self.recover()

    def recover(self):
        window = self.window
        if window.generation.worker or not self.confirm_discard():
            return
        snapshots = self.recovery.snapshots()
        if not snapshots:
            Dialogs.information(window, "Recovery", "There are no autosaved projects yet.")
            return
        path, _ = Dialogs.getOpenFileName(
            window, "Recover project", str(snapshots[0]), "Project (*.rmapproj)"
        )
        if path:
            self.read_project(path)
            window.document.path = None
            window.set_dirty()
