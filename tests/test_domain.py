import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import soundfile as sf

from rhythia_studio.audio import analyze
from rhythia_studio.editing import History, move_notes, replace_region
from rhythia_studio.generation import generate
from rhythia_studio.models import LEVELS, Cancelled
from rhythia_studio.project import RecoveryStore, export_rhm, load_project, save_project
from rhythia_studio.quality import evaluate, validate
from rhythia_studio.services import GenerationService
from rhythia_studio.structure import detect_sections
from rhythia_studio.timing import estimate_timing


def click_audio(path, bpm=120, seconds=24):
    sr = 22050
    y = np.zeros(sr * seconds, dtype="float32")
    for t in np.arange(0.5, seconds - 0.5, 60 / bpm):
        i = int(t * sr)
        y[i : i + 600] = np.random.default_rng(0).normal(0, 0.5, 600) * np.exp(-np.arange(600) / 100)
    sf.write(path, y, sr)


class AnalysisTests(unittest.TestCase):
    def test_variable_tempo_follows_known_change(self):
        times = np.arange(0, 64000, 10)
        flux = np.zeros(len(times))
        beats = np.r_[np.arange(500, 32000, 500), np.arange(32000, 64000, 60000 / 132)]
        flux[np.rint(beats / 10).astype(int)] = 1
        analysis = estimate_timing(times, flux, 64000, bpm=120, variable=True)
        points = analysis["timing_points"]
        self.assertAlmostEqual(points[0]["Bpm"], 120, delta=0.1)
        self.assertGreater(points[-1]["Bpm"], 128)
        self.assertLess(points[-1]["Bpm"], 134)
        self.assertTrue(np.all(np.diff(analysis["beats_ms"]) > 0))

    def test_timing_matches_known_clicks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pulse.wav"
            click_audio(path)
            a = analyze(path)
            self.assertAlmostEqual(a["bpm"], 120, delta=0.5)
            beats = np.asarray(a["beats_ms"])
            distances = np.minimum(beats % 500, 500 - beats % 500)
            self.assertLess(float(np.median(distances)), 45)
            for level in LEVELS:
                notes = generate(a, level)
                validate(notes, a["duration_ms"])
                self.assertEqual(notes, generate(a, level))
                self.assertTrue(
                    all(
                        w["message"].startswith("Cambio")
                        for w in evaluate(notes, a["duration_ms"], level)["warnings"]
                    )
                )

    def test_repeated_features_with_distractors(self):
        rng = np.random.default_rng(3)
        theme = rng.random((64, 20))
        distractor = rng.random((64, 20))
        features = np.vstack((theme, distractor, theme + rng.normal(0, 0.025, theme.shape)))
        a = dict(
            features=features.tolist(),
            feature_times_ms=(np.arange(192) * 250).tolist(),
            duration_ms=48000,
            bpm=120,
        )
        result = detect_sections(a, 0.85)
        first = next(s for s in result if s["start_ms"] == 0)
        repeat = next(s for s in result if s["start_ms"] == 32000)
        self.assertTrue(first["repeated"])
        self.assertEqual(first["group"], repeat["group"])
        self.assertFalse(any(s["repeated"] for s in result if 16000 <= s["start_ms"] < 32000))

    def test_pattern_reuse(self):
        ts = np.arange(0, 16000, 20)
        flux = np.where(ts % 250 == 0, 1.0, 0.05)
        # Use a pulse every 500ms, exactly represented on the analysis frame grid.
        flux = np.where(ts % 500 == 0, 1.0, 0.05)
        a = dict(
            duration_ms=16000,
            bpm=120,
            times_ms=ts.tolist(),
            flux=flux.tolist(),
            energy=np.ones(len(ts)).tolist(),
            beats_ms=np.arange(0, 16000, 500).tolist(),
            onsets_ms=np.arange(500, 16000, 500).tolist(),
            sections=[
                dict(start_ms=0, end_ms=8000, group="R1", repeated=True),
                dict(start_ms=8000, end_ms=16000, group="R1", repeated=True),
            ],
        )
        notes = generate(a, "Normal")
        first = {n["Time"]: (n["X"], n["Y"]) for n in notes if n["Time"] < 8000}
        second = {n["Time"] - 8000: (n["X"], n["Y"]) for n in notes if n["Time"] >= 8000}
        common = set(first) & set(second)
        self.assertGreater(len(common), 10)
        self.assertGreater(sum(first[t] == second[t] for t in common) / len(common), 0.9)

    def test_cancel_and_silence(self):
        with self.assertRaises(Cancelled):
            analyze("not-read.wav", cancel=lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "silence.wav"
            sf.write(path, np.zeros(22050 * 4), 22050)
            with self.assertRaises(ValueError):
                analyze(path)


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        path = self.folder / "pulse.wav"
        click_audio(path, seconds=8)
        self.project, self.audio = GenerationService().create(path)

    def tearDown(self):
        self.temp.cleanup()

    def test_project_and_rhm_roundtrip(self):
        path = self.folder / "project.rmapproj"
        save_project(path, self.project, self.audio)
        self.assertEqual(load_project(path), (self.project, self.audio))
        for level in LEVELS:
            path = self.folder / (level + ".rhm")
            export_rhm(path, self.project, level, self.audio)
            with zipfile.ZipFile(path) as z:
                data = json.loads(z.read("map"))
                self.assertEqual(z.read("audio"), self.audio)
                self.assertTrue(z.read("cover").startswith(b"\x89PNG"))
                self.assertTrue(all(set(n) == {"Time", "X", "Y"} for n in data["Notes"]))
                self.assertEqual(len(data["Notes"]), len(self.project["maps"][level]))
                self.assertGreater(data["TimingPoints"][0]["Bpm"], 0)

    def test_region_keeps_outside_and_manual_notes(self):
        existing = [dict(Time=t, X=0, Y=0, Edited=t == 500) for t in (100, 500, 900, 1400)]
        generated = [dict(Time=t, X=1, Y=1) for t in (100, 510, 800, 1400)]
        result = replace_region(existing, generated, 400, 1000, True)
        self.assertEqual(result[0], existing[0])
        self.assertEqual(result[-1], existing[-1])
        self.assertIn(existing[1], result)
        self.assertFalse(any(n["Time"] == 510 for n in result))
        self.assertTrue(any(n["Time"] == 800 for n in result))

    def test_undo_redo_and_invalid_batch_edit(self):
        history = History()
        before = copy.deepcopy(self.project)
        history.push(self.project)
        self.project["maps"]["Normal"][0]["X"] = 2
        changed = copy.deepcopy(self.project)
        restored = history.undo(self.project)
        self.assertEqual(restored, before)
        self.assertEqual(history.redo(restored), changed)
        with self.assertRaises(ValueError):
            move_notes([dict(Time=100, X=2, Y=0)], [0], dx=1, duration=1000)
        with self.assertRaises(ValueError):
            move_notes(
                [dict(Time=100, X=0, Y=0), dict(Time=200, X=1, Y=0)], [0], time_delta=100, duration=1000
            )

    def test_recovery_and_tampered_audio(self):
        store = RecoveryStore(self.folder / "recovery")
        store.save(self.project, self.audio)
        self.assertEqual(len(store.snapshots()), 1)
        self.assertEqual(load_project(store.snapshots()[0]), (self.project, self.audio))
        store.discard(self.project)
        self.assertFalse(store.snapshots())
        with self.assertRaises(ValueError):
            save_project(self.folder / "bad.rmapproj", self.project, b"changed")


if __name__ == "__main__":
    unittest.main()
