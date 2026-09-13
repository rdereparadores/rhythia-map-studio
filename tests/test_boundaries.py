"""Regression tests for contracts shared by persistence, cache and workers."""

import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from test_domain import click_audio

from rhythia_studio.i18n import Translator
from rhythia_studio.messages import Message, MessageError
from rhythia_studio.models import Settings
from rhythia_studio.project import load_project, save_project
from rhythia_studio.services import GenerationService
from rhythia_studio.snapshots import snapshot_project


class BoundaryTests(unittest.TestCase):
    def test_unsupported_project_versions_are_rejected(self):
        for version in (0, 2, 3, True, "1", None):
            with self.subTest(version=version):
                project = json.loads(json.dumps(self.project))
                project["version"] = version
                path = self.root / "unsupported.rmapproj"
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("project.json", json.dumps(project))
                    archive.writestr("audio", self.audio)
                with self.assertRaisesRegex(ValueError, "Unsupported project version"):
                    load_project(path)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.song = self.root / "pulse.wav"
        click_audio(self.song, seconds=8)
        self.service = GenerationService()
        self.project, self.audio = self.service.create(self.song)

    def test_nested_analysis_cannot_mutate_cache_or_history(self):
        snapshot = snapshot_project(self.project)
        self.assertIs(snapshot["analysis"], self.project["analysis"])
        with self.assertRaises(TypeError):
            snapshot["analysis"]["energy"][0] = 999
        with self.assertRaises(TypeError):
            snapshot["analysis"]["sections"][0]["group"] = "changed"
        self.project["maps"]["Normal"][0]["X"] = 2
        self.assertIsNot(snapshot["maps"], self.project["maps"])
        cached, _ = self.service.create(self.song)
        self.assertEqual(cached["maps"], snapshot["maps"])

    def test_mutable_input_snapshot_is_also_isolated(self):
        editable = json.loads(json.dumps(self.project))
        snapshot = snapshot_project(editable)
        editable["analysis"]["energy"][0] = 999
        self.assertNotEqual(snapshot["analysis"]["energy"][0], 999)

    def test_invalid_project_structures_fail_at_load(self):
        def edit_project(*path, value):
            project = json.loads(json.dumps(self.project))
            node = project
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = value
            return project

        cases = [
            edit_project("analysis", "energy", value=[]),
            edit_project("analysis", "beats_ms", value=[500, 100]),
            edit_project("analysis", "flux", 0, value=float("nan")),
            edit_project("analysis", "sections", 0, "end_ms", value=999999),
            edit_project("analysis", "phrases", 0, "lead", value="unknown"),
            edit_project("settings", "separation", value="false"),
            edit_project("maps", "Normal", 0, "Source", value=[]),
            {"version": 1},
            [],
        ]
        for project in cases:
            with self.subTest(project=str(project)[:80]):
                path = self.root / "invalid.rmapproj"
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("project.json", json.dumps(project))
                    archive.writestr("audio", self.audio)
                with self.assertRaises(ValueError):
                    load_project(path)

    def test_failed_atomic_replace_preserves_previous_project(self):
        path = self.root / "saved.rmapproj"
        save_project(path, self.project, self.audio)
        original = path.read_bytes()
        changed = copy.deepcopy(self.project)
        changed["title"] = "Changed"
        with patch("rhythia_studio.project.os.replace", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                save_project(path, changed, self.audio)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_dynamic_messages_do_not_parse_or_translate_user_content(self):
        translator = Translator("en")
        path = "Project saved: {untrusted}.rmapproj"
        self.assertEqual(translator.text(path), path)
        self.assertEqual(
            translator.text(Message("Project saved: {detail}", detail=path)),
            "Project saved: " + path,
        )
        error = MessageError("Invalid project field: {field}.", field="analysis.energy")
        status = Message("Autosave failed: {detail}", detail=error)
        self.assertEqual(translator.text(status), "Autosave failed: Invalid project field: analysis.energy.")
        self.assertEqual(
            translator.text("The {source} track is not aligned with the song.", source="vocals"),
            "The vocals track is not aligned with the song.",
        )

    def test_settings_reject_invalid_numeric_and_boolean_types(self):
        for settings in ({"density": True}, {"seed": 1.2}, {"bpm": float("inf")}, {"separation": "yes"}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                Settings(**settings)

    def test_worker_records_traceback_and_preserves_structured_error(self):
        from unittest.mock import Mock

        from rhythia_studio.ui.workers import GenerationWorker, SaveWorker

        error = MessageError("Invalid project field: {field}.", field="audio")
        service = Mock()
        service.create.side_effect = error
        store = Mock()
        store.save.side_effect = error
        workers = (
            GenerationWorker(service, self.song, Settings()),
            SaveWorker(store, self.project, self.audio),
        )
        for worker in workers:
            received = []
            worker.failed.connect(received.append)
            with self.assertLogs("rhythia_studio.ui.workers", level="ERROR") as logs:
                worker.run()
            self.assertEqual(received, [error])
            self.assertIsNotNone(logs.records[0].exc_info)
