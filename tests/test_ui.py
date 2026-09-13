import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import copy
import tempfile
import time
import unittest
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from test_domain import click_audio

from rhythia_studio.project import save_project
from rhythia_studio.services import GenerationService
from rhythia_studio.ui.window import Studio


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        font = Path("C:/Windows/Fonts/segoeui.ttf")
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        audio = self.root / "pulse.wav"
        click_audio(audio, seconds=8)
        p, a = GenerationService().create(audio)
        save_project(self.root / "test.rmapproj", p, a)
        self.window = Studio(
            self.root / "test.rmapproj",
            self.root / "recovery",
            offer_recovery=False,
            language="en",
            persist_language=False,
        )
        self.window.playback.audio_out.setVolume(0)
        self.window.show()
        self.app.processEvents()

    def settle(self, condition, timeout=10):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        self.app.processEvents()
        self.assertTrue(condition())

    def tearDown(self):
        self.settle(
            lambda: self.window.generation.worker is None and self.window.documents.save_worker is None
        )
        self.window.set_dirty(False)
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def test_edit_undo_redo_and_zoom(self):
        w = self.window
        before = copy.deepcopy(w.editor.current_notes())
        w.view.table.selectRow(1)
        w.editor.move_note(1, 1)
        self.assertTrue(w.editor.current_notes()[1]["Edited"])
        w.editor.undo()
        self.assertEqual(w.editor.current_notes(), before)
        w.editor.redo()
        self.assertTrue(w.editor.current_notes()[1]["Edited"])
        w.view.timeline.zoom(0.5)
        self.assertLess(w.view.timeline.span, w.view.timeline.duration)
        w.playback.set_region(1000, 3000)
        self.assertEqual(w.playback.region(), (1000, 3000))

    def test_save_asks_for_first_path_then_reuses_it(self):
        from unittest.mock import patch

        from rhythia_studio.project import load_project

        window = self.window
        window.document.path = None
        window.set_dirty()
        destination = self.root / "chosen"
        with patch(
            "rhythia_studio.ui.dialogs.Dialogs.getSaveFileName", return_value=(str(destination), "")
        ) as dialog:
            self.assertTrue(window.documents.save())
            window.documents.change_title("Saved again")
            self.assertTrue(window.documents.save())
            self.assertEqual(dialog.call_count, 1)
        project, _ = load_project(str(destination) + ".rmapproj")
        self.assertEqual(project["title"], "Saved again")
        self.assertFalse(window.document.dirty)

    def test_cancelled_save_keeps_dirty_document_without_a_path(self):
        from unittest.mock import patch

        window = self.window
        window.document.path = None
        window.set_dirty()
        with patch("rhythia_studio.ui.dialogs.Dialogs.getSaveFileName", return_value=("", "")):
            self.assertFalse(window.documents.save())
        self.assertIsNone(window.document.path)
        self.assertTrue(window.document.dirty)

    def test_generation_installs_on_the_ui_thread(self):
        from unittest.mock import patch

        from PySide6.QtCore import QThread

        window = self.window
        observed = []
        install = window.documents.install

        def capture(project, audio):
            observed.append(QThread.currentThread())
            return install(project, audio)

        with patch.object(window.documents, "install", side_effect=capture):
            window.documents.choose_audio(self.root / "pulse.wav")
            window.generation.regenerate()
            self.settle(lambda: window.generation.worker is None)
        self.assertEqual(observed, [self.app.thread()])

    def test_basic_view_and_advanced_disclosure_preserve_settings(self):
        w = self.window
        self.assertFalse(w.view.emphasis.isVisible())
        self.assertTrue(w.view.level.isVisible())
        self.assertTrue(w.view.generate_btn.isVisible())
        self.assertFalse(w.view.bpm.isVisible())
        self.assertFalse(w.view.tabs.isVisible())
        w.view.advanced_toggle.click()
        self.assertTrue(w.view.bpm.isVisible())
        self.assertTrue(w.view.tabs.isVisible())
        w.view.density.setValue(1.2)
        w.view.loop.setChecked(True)
        w.view.rate.setCurrentIndex(0)
        w.view.table.selectRow(1)
        w.view.advanced_toggle.click()
        self.assertFalse(w.view.tabs.isVisible())
        self.assertFalse(w.view.timeline.isVisible())
        self.assertFalse(w.view.loop.isChecked())
        self.assertEqual(w.playback.player.playbackRate(), 1)
        self.assertEqual(w.editor.selected_indices(), [])
        self.assertEqual(w.settings().density, 1.2)

    def test_song_selection_waits_for_generate_and_exports_selected_level(self):
        w = self.window
        before = copy.deepcopy(w.document.project)
        w.documents.choose_audio(self.root / "pulse.wav")
        self.assertIsNone(w.generation.worker)
        self.assertEqual(w.document.project, before)
        self.assertTrue(w.view.generate_btn.isEnabled())
        self.assertFalse(w.view.export_btn.isEnabled())
        self.assertFalse(w.view.preview.isVisible())
        w.view.level.setCurrentText("Easy")
        w.generation.regenerate()
        self.settle(lambda: w.generation.worker is None)
        self.assertIsNone(w.document.pending_audio)
        self.assertTrue(w.view.export_btn.isEnabled())
        self.assertEqual(w.view.level.currentText(), "Easy")
        self.assertEqual(w.editor.current_notes(), w.document.project["maps"]["Easy"])

    def test_priority_tracks_separation_and_restores_mix_orientation(self):
        w = self.window
        self.assertGreater(w.view.phrases_table.rowCount(), 0)
        w.view.separate_audio.setChecked(True)
        w.view.emphasis.setCurrentText("Vocals")
        w.view.variation.setValue(1.5)
        settings = w.settings()
        self.assertTrue(settings.separation)
        self.assertEqual(settings.emphasis, "Vocals")
        self.assertEqual(settings.variation, 1.5)
        w.document.project["settings"] = settings.to_dict()
        w.view.variation.setValue(0)
        w.apply_settings()
        self.assertEqual(w.view.variation.value(), 1.5)
        w.view.separate_audio.setChecked(False)
        self.assertFalse(w.view.emphasis.isVisible())
        self.assertEqual(w.settings().emphasis, "Mix")
        self.assertFalse(w.view.mix_emphasis.isVisible())
        w.view.advanced_toggle.click()
        self.assertTrue(w.view.mix_emphasis.isVisible())
        w.view.mix_emphasis.setCurrentText("Percussive")
        self.assertEqual(w.settings().emphasis, "Percussion")
        w.document.project["settings"] = w.settings().to_dict()
        w.view.mix_emphasis.setCurrentIndex(0)
        w.apply_settings()
        self.assertEqual(w.settings().emphasis, "Percussion")
        w.view.separate_audio.setChecked(True)
        self.assertTrue(w.view.emphasis.isVisible())
        self.assertFalse(w.view.mix_emphasis.isVisible())
        self.assertEqual(w.settings().emphasis, "Vocals")

    def test_cancel_retains_document(self):
        w = self.window
        before = copy.deepcopy(w.document.project)
        w.generation.start_job(w.playback.audio_path, "all")
        w.generation.cancel_generation()
        self.settle(lambda: w.generation.worker is None)
        self.assertEqual(w.document.project, before)
        self.assertTrue(w.view.generate_btn.isEnabled())

    def test_language_switch_preserves_project_settings_and_selection(self):
        w = self.window
        w.view.advanced_toggle.click()
        w.view.level.setCurrentText("Hard")
        w.view.style.setCurrentText("Jumps")
        w.view.table.selectRow(1)
        w.view.loop.setChecked(True)
        w.view.rate.setCurrentIndex(0)
        before = copy.deepcopy(w.document.project)
        settings = w.settings()
        w.view.language.setCurrentIndex(w.view.language.findData("en"))
        self.assertEqual(w.view.save_btn.text(), "Save")
        self.assertEqual(w.view.level.currentText(), "Hard")
        self.assertEqual(w.view.level.currentData(), "Hard")
        self.assertEqual(w.settings(), settings)
        self.assertEqual(w.document.project, before)
        self.assertEqual(w.editor.selected_indices(), [1])
        self.assertEqual(w.playback.player.playbackRate(), 0.5)
        self.assertTrue(w.view.loop.isChecked())
        self.assertEqual(w.view.tabs.tabText(0), "Notes")
        self.assertIn("Ready to export", w.view.stats.text())
        w.show_status("Analyzing attacks, harmony and timbre…")
        self.assertEqual(w.statusBar().currentMessage(), "Analyzing attacks, harmony and timbre…")
        w.view.language.setCurrentIndex(w.view.language.findData("es"))
        self.assertEqual(w.view.save_btn.text(), w.t("Save"))
        self.assertEqual(w.view.level.currentText(), w.t("Hard"))
        self.assertEqual(w.settings(), settings)

    def test_english_regeneration_uses_canonical_map_keys(self):
        w = self.window
        w.view.language.setCurrentIndex(w.view.language.findData("en"))
        w.view.level.setCurrentIndex(w.view.level.findData("Easy"))
        w.generation.regenerate()
        self.settle(lambda: w.generation.worker is None)
        self.assertEqual(set(w.document.project["maps"]), {"Easy", "Normal", "Hard"})
        self.assertEqual(w.document.project["settings"]["style"], "Flowing")
        self.assertEqual(w.view.level.currentText(), "Easy")
        self.assertTrue(w.editor.current_notes())

    def test_all_static_ui_strings_have_catalog_entries(self):
        from rhythia_studio.i18n import Translator

        catalog = Translator("en").messages
        for _, _, source in self.window.ui_translations.bindings:
            if source and any(character.isalpha() for character in source) and source != "Rhythia Map Studio":
                self.assertIn(source, catalog)

    def test_language_preference_survives_reopening(self):
        from unittest.mock import patch

        from PySide6.QtCore import QSettings

        preferences = QSettings(str(self.root / "preferences.ini"), QSettings.IniFormat)
        with patch("rhythia_studio.ui.window.QSettings", return_value=preferences):
            first = Studio(recovery_directory=self.root / "other-recovery", offer_recovery=False)
            first.view.language.setCurrentIndex(first.view.language.findData("en"))
            first.close()
            second = Studio(recovery_directory=self.root / "other-recovery", offer_recovery=False)
            self.assertEqual(second.translator.language, "en")
            self.assertEqual(second.view.save_btn.text(), "Save")
            second.close()

    def test_regenerate_region_and_autosave(self):
        w = self.window
        outside = [dict(n) for n in w.editor.current_notes() if not 2000 <= n["Time"] < 4000]
        w.playback.set_region(2000, 4000)
        w.view.seed.setValue(74)
        w.generation.regenerate_region()
        self.settle(lambda: w.generation.worker is None)
        self.assertEqual([n for n in w.editor.current_notes() if not 2000 <= n["Time"] < 4000], outside)
        self.settle(lambda: w.documents.save_worker is None)
        self.assertTrue(w.documents.recovery.snapshots())


if __name__ == "__main__":
    unittest.main()
