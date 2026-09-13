"""Desktop controller: coordinates widgets, document edits and asynchronous jobs."""

from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, QSettings, QSignalBlocker, QStandardPaths, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QTableWidgetItem

from .. import __version__
from ..arrangement import SOURCE_LABELS
from ..document import DocumentSession
from ..i18n import Translator
from ..models import Settings
from ..quality import evaluate
from ..structure import repetition_summary
from .controllers.documents import DocumentController
from .controllers.editor import EditorController
from .controllers.generation import GenerationController
from .controllers.playback import PlaybackController
from .dialogs import Dialogs
from .layout import build_ui
from .localization import UiTranslations
from .view import StudioView


class Studio(QMainWindow):
    def __init__(
        self,
        project_path=None,
        recovery_directory=None,
        offer_recovery=True,
        language=None,
        persist_language=True,
    ):
        super().__init__()
        self.preferences = QSettings("LocalTools", "RhythiaMapStudio") if persist_language else None
        preferred = language or (self.preferences.value("language", "en") if self.preferences else "en")
        self.translator = Translator(preferred)
        self.t = self.translator.text
        self.status_source = ""
        self.setWindowTitle(f"Rhythia Map Studio · {__version__}")
        self.setMinimumSize(1040, 800)
        self.resize(1160, 840)
        self.document = DocumentSession()
        self.issues_data = []
        recovery_directory = (
            recovery_directory
            or Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "recovery"
        )
        self.documents = DocumentController(self, recovery_directory)
        self.generation = GenerationController(self)
        self.playback = PlaybackController(self)
        self.editor = EditorController(self)
        self.view = StudioView()
        build_ui(self, self.view)
        self.ui_translations = UiTranslations(self)
        self.ui_translations.apply(self)
        for key, callback in [
            ("Ctrl+S", self.documents.save),
            ("Ctrl+Z", self.editor.undo),
            ("Ctrl+Shift+Z", self.editor.redo),
            ("Ctrl+Y", self.editor.redo),
        ]:
            QShortcut(QKeySequence(key), self, activated=callback)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(30000)
        self.autosave_timer.timeout.connect(self.documents.autosave)
        self.autosave_timer.start()
        self.refresh()
        self.update_language_labels()
        if project_path:
            self.documents.read_project(project_path)
        if offer_recovery and self.documents.recovery.snapshots():
            QTimer.singleShot(300, self.documents.offer_recovery)

    def error(self, message):
        Dialogs.warning(self, "Unable to complete", message)

    def show_status(self, message):
        self.status_source = message
        self.statusBar().showMessage(self.t(self.status_source))

    def change_language(self, *args):
        if not hasattr(self, "ui_translations"):
            return
        selected = self.editor.selected_indices()
        self.translator.set_language(self.view.language.currentData())
        if self.preferences:
            self.preferences.setValue("language", self.translator.language)
        self.ui_translations.apply(self)
        self.refresh()
        blocker = QSignalBlocker(self.view.table)
        for index in selected:
            self.view.table.selectionModel().select(
                self.view.table.model().index(index, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
            )
        del blocker
        self.view.grid.selected = selected[0] if selected else -1
        self.update_language_labels()

    def update_language_labels(self):
        self.set_dirty(self.document.dirty)
        if not self.document.project and not self.document.pending_audio:
            self.view.song.setText(self.t("Choose a song to get started"))
            self.view.preview_title.setText(self.t("Your map starts with a song"))
        self.view.advanced_toggle.setText(
            self.t("Hide advanced options" if self.view.advanced_toggle.isChecked() else "Advanced options")
        )
        self.view.preview_hint.setText(
            self.t(
                "Select notes to edit them. The preview shows positions, not the in-game camera."
                if self.view.advanced_toggle.isChecked()
                else "Listen and preview your map before exporting."
            )
        )
        self.playback.playback_changed(self.playback.player.playbackState())
        self.show_status(self.status_source)

    def set_advanced(self, visible):
        for widget in self.view.advanced_widgets:
            widget.setVisible(visible)
        self.view.advanced_toggle.setText(self.t("Hide advanced options" if visible else "Advanced options"))
        self.view.grid.selected = -1
        self.view.table.clearSelection()
        self.view.grid.update()
        if not visible:
            self.view.loop.setChecked(False)
            self.view.rate.setCurrentIndex(2)
            self.view.timeline.show_all()
        self.view.preview_hint.setText(
            self.t(
                "Select notes to edit them. The preview shows positions, not the in-game camera."
                if visible
                else "Listen and preview your map before exporting."
            )
        )

    def set_dirty(self, value=True):
        self.document.dirty = value
        self.setWindowTitle(
            f"Rhythia Map Studio · {__version__}" + (self.t(" • unsaved changes") if value else "")
        )

    def settings(self):
        return Settings(
            bpm=self.view.bpm.value(),
            density=self.view.density.value(),
            offset=self.view.offset.value(),
            seed=self.view.seed.value(),
            style=self.view.style.currentData(),
            repeat_patterns=self.view.repeat.isChecked(),
            similarity=self.view.similarity.value(),
            variable_tempo=self.view.variable.isChecked(),
            emphasis=(
                self.view.emphasis if self.view.separate_audio.isChecked() else self.view.mix_emphasis
            ).currentData(),
            separation=self.view.separate_audio.isChecked(),
            variation=self.view.variation.value(),
        )

    def update_priority_controls(self, *args):
        separated = self.view.separate_audio.isChecked()
        self.view.basic_form.setRowVisible(self.view.emphasis, separated)
        self.view.generation_form.setRowVisible(self.view.mix_emphasis, not separated)
        if not separated:
            self.view.mix_emphasis.setCurrentIndex(0)

    def apply_settings(self):
        settings = Settings.from_dict(self.document.project["settings"])
        self.view.bpm.setValue(settings.bpm)
        self.view.density.setValue(settings.density)
        self.view.offset.setValue(settings.offset)
        self.view.seed.setValue(settings.seed)
        self.view.style.setCurrentIndex(self.view.style.findData(settings.style))
        self.view.repeat.setChecked(settings.repeat_patterns)
        self.view.similarity.setValue(settings.similarity)
        self.view.variable.setChecked(settings.variable_tempo)
        if settings.separation:
            self.view.emphasis.setCurrentIndex(self.view.emphasis.findData(settings.emphasis))
        self.view.separate_audio.setChecked(settings.separation)
        if not settings.separation:
            self.view.mix_emphasis.setCurrentIndex(self.view.mix_emphasis.findData(settings.emphasis))
        self.view.variation.setValue(settings.variation)

    def scale_tempo(self, factor):
        current = self.view.bpm.value() or (
            self.document.project["analysis"]["bpm"] if self.document.project else 120
        )
        self.view.bpm.setValue(min(300, max(35, current * factor)))

    def refresh_busy(self):
        busy = bool(self.generation.worker)
        active = bool(self.document.project) and not self.document.pending_audio and not busy
        for window in (
            self.view.save_btn,
            self.view.export_btn,
            self.view.generate_btn,
            self.view.region_btn,
            self.view.play_btn,
        ):
            window.setEnabled(active)
        for window in (self.view.import_btn, self.view.open_btn, self.view.recover_btn):
            window.setEnabled(not busy)
        for window in (
            self.view.tabs,
            self.view.grid,
            self.view.timeline,
            self.view.title_edit,
            self.view.level,
        ):
            window.setEnabled(not busy)
        self.view.generate_btn.setEnabled(
            bool(self.document.project or self.document.pending_audio) and not busy
        )
        for window in (self.view.advanced_settings, self.view.emphasis, self.view.separate_audio):
            window.setEnabled(not busy)
        self.view.generate_btn.setText(
            self.t(
                "Generate map"
                if self.document.pending_audio or not self.document.project
                else "Regenerate map"
            )
        )
        self.view.progress.setVisible(busy)
        self.view.cancel_btn.setVisible(busy)

    def fill_table(self, target, rows):
        target.blockSignals(True)
        target.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem(self.t(value))
                item.setToolTip(self.t(value))
                target.setItem(i, j, item)
        target.clearSelection()
        target.blockSignals(False)

    def refresh(self, *args):
        self.refresh_busy()
        self.view.preview.setVisible(bool(self.document.project) and not self.document.pending_audio)
        self.view.empty_state.setVisible(not self.document.project or bool(self.document.pending_audio))
        self.view.transport.setVisible(bool(self.document.project) and not self.document.pending_audio)
        if self.document.pending_audio:
            self.view.preview_title.setText(self.document.pending_audio.stem)
            self.view.stats.setText(
                self.t("Song ready. Choose your difficulty and priority, then select Generate map.")
            )
            return
        if not self.document.project:
            self.view.stats.setText(self.t("Choose a song to create your first map."))
            return
        analysis = self.document.project["analysis"]
        notes = self.editor.current_notes()
        quality = evaluate(notes, analysis["duration_ms"], self.view.level.currentData())
        repeat = repetition_summary(analysis.get("sections", []))
        self.view.preview_title.setText(self.document.project["title"])
        self.view.stats.setText(
            self.t(
                "{level} · {count} notes · Ready to export",
                level=self.t(self.view.level.currentData()),
                count=len(notes),
            )
        )
        self.view.stats.setToolTip(
            self.t(
                "{count} notes · {nps} notes/s · Peak {peak}/s · {bpm} BPM · {groups} repeated groups · {warnings} warnings",
                count=len(notes),
                nps=quality["nps"],
                peak=quality["peak_nps"],
                bpm=f"{analysis['bpm']:.3f}",
                groups=repeat["groups"],
                warnings=len(quality["warnings"]),
            )
        )
        self.fill_table(
            self.view.table,
            [
                (
                    f"{n['Time'] / 1000:.3f}",
                    n["X"],
                    n["Y"],
                    SOURCE_LABELS.get(n.get("Source", "mix"), "Manual"),
                )
                for n in notes
            ],
        )
        self.view.grid.notes = notes
        self.view.grid.selected = -1
        self.view.grid.update()
        self.view.timeline.notes = notes
        self.view.timeline.update()
        self.fill_table(
            self.view.sections_table,
            [
                (
                    settings["group"],
                    f"{settings['start_ms'] / 1000:.2f}",
                    f"{(settings['end_ms'] - settings['start_ms']) / 1000:.2f}",
                    f"{settings['similarity']:.0%}" if settings["repeated"] else "—",
                )
                for settings in analysis["sections"]
            ],
        )
        self.issues_data = quality["warnings"]
        self.fill_table(
            self.view.phrases_table,
            [
                (
                    f"{phrase['start_ms'] / 1000:.2f}",
                    phrase["lead_label"],
                    phrase["role"],
                    f"{phrase['intensity']:.0%}",
                )
                for phrase in analysis.get("phrases", [])
            ],
        )
        self.fill_table(
            self.view.issues, [(f"{i['time_ms'] / 1000:.3f}", i["message"]) for i in self.issues_data]
        )

    def closeEvent(self, event):
        if self.generation.worker:
            self.generation.worker.cancel()
            self.show_status("Cancelling analysis before closing…")
            event.ignore()
            QTimer.singleShot(150, self.close)
            return
        if self.documents.save_worker:
            event.ignore()
            QTimer.singleShot(150, self.close)
            return
        if not self.documents.confirm_discard():
            event.ignore()
            return
        self.autosave_timer.stop()
        self.playback.shutdown()
        event.accept()
