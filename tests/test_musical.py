"""Regression contracts for phrase arrangement, motion and separated audio."""

import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from rhythia_studio.arrangement import build_arrangement
from rhythia_studio.generation import add_candidate, thin_candidates
from rhythia_studio.models import Cancelled, Settings
from rhythia_studio.musical_features import SOURCES, attach_stems
from rhythia_studio.planner import movement_intents, plan_positions, repeat_diagnostics, shape_key
from rhythia_studio.separation import SeparationEngine


class MusicalTests(unittest.TestCase):
    def test_rotation_and_reflection_do_not_hide_loops(self):
        self.assertEqual(shape_key((0, 1, 4, 5)), shape_key((2, 1, 4, 3)))
        motif = (0, 1, 2, 5, 4, 3, 6, 7)
        notes = [dict(X=i % 3, Y=i // 3) for i in motif * 12]
        self.assertGreater(repeat_diagnostics(notes)["longest_consecutive_repeat_windows"], 70)

    def test_long_phrase_avoids_loops_and_preserves_events_with_speed_limits(self):
        phrase = dict(start_ms=0, end_ms=24000, intensity=0.7, part=0, role="intro", lead="vocals")
        events = [dict(time=i * 250, accent=i % 4 == 0, pitch=60, pitch_confidence=0) for i in range(96)]
        intents = movement_intents(events, phrase, 42)
        notes = plan_positions(intents, 10)
        self.assertEqual([n["time"] for n in notes], [n["time"] for n in events])
        self.assertLess(repeat_diagnostics(notes)["longest_consecutive_repeat_windows"], 5)
        for a, b in zip(notes, notes[1:], strict=False):
            self.assertLessEqual(math.dist((a["X"], a["Y"]), (b["X"], b["Y"])), 2.5 + 1e-8)
        self.assertEqual(notes, plan_positions(intents, 10))
        with self.assertRaises(Cancelled):
            plan_positions(intents, 10, cancel=lambda: True)

    def test_pitch_moves_target_upward_only_when_confident(self):
        phrase = dict(start_ms=0, end_ms=1000, intensity=0.5, part=0, role="intro", lead="vocals")
        events = [dict(time=500, pitch=p, pitch_confidence=1) for p in (55, 65, 75)]
        intents = movement_intents(events, phrase, 42)
        self.assertGreater(intents[0]["target"][1], intents[-1]["target"][1])
        unpitched = movement_intents([dict(e, pitch_confidence=0) for e in events], phrase, 42)
        self.assertEqual(unpitched[0]["target"], unpitched[-1]["target"])

    def test_lead_selection_avoids_vocal_leak_and_follows_priority(self):
        ts = np.arange(0, 16000, 20)
        analysis = dict(
            times_ms=ts,
            energy=np.ones(len(ts)),
            bpm=120,
            sections=[dict(start_ms=0, end_ms=16000, group="A")],
        )

        def source(presence):
            return dict(
                relative_energy=np.full(len(ts), presence),
                flux=np.full(len(ts), 0.5),
                pitch_confidence=np.full(len(ts), 0.4),
                energy=np.ones(len(ts)),
            )

        analysis["sources"] = {s: source(0.5) for s in SOURCES}
        analysis["sources"]["vocals"] = source(0.01)
        self.assertNotIn("vocals", [p["lead"] for p in build_arrangement(analysis, "Vocals")])
        self.assertEqual({"drums"}, {p["lead"] for p in build_arrangement(analysis, "Percussion")})
        analysis["sources"]["vocals"] = source(0.6)
        self.assertEqual({"vocals"}, {p["lead"] for p in build_arrangement(analysis, "Vocals")})

    def test_breath_removes_weak_tail_but_keeps_strong_accent(self):
        ts = [0, 500, 950, 999]
        curve = dict(
            energy=[1] * 4,
            relative_energy=[1] * 4,
            flux=[0.5, 0.5, 0.5, 1.4],
            pitch=[60] * 4,
            pitch_confidence=[0] * 4,
        )
        phrase = dict(lead="vocals", start_ms=0, end_ms=1000, breath=True, group="A")
        candidates = []
        for t in (500, 950, 999):
            add_candidate(candidates, dict(bpm=120), ts, curve, phrase, 0.2, t)
        self.assertEqual([e["time"] for e in candidates], [500, 999])
        self.assertEqual(
            thin_candidates([dict(time=100, strength=0.2), dict(time=150, strength=1)], 100)[0]["time"], 150
        )

    def test_stem_alignment_and_serializable_features(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = {}
            for source in SOURCES:
                path = Path(folder) / (source + ".wav")
                sf.write(path, np.zeros((22050, 2)), 22050)
                paths[source] = path
            analysis = dict(duration_ms=1000, times_ms=list(range(0, 1000, 20)))
            attach_stems(analysis, paths)
            json.dumps(analysis)
            self.assertEqual(set(analysis["sources"]), set(SOURCES))
            self.assertTrue(all(v == 0 for v in analysis["sources"]["vocals"]["pitch_confidence"]))
            analysis["duration_ms"] = 1100
            with self.assertRaisesRegex(ValueError, "aligned"):
                attach_stems(analysis, paths)

    def test_missing_separator_and_invalid_settings_are_explicit(self):
        with self.assertRaises(ValueError):
            Settings(emphasis="Vocals", separation=False)
        with self.assertRaises(ValueError):
            Settings(variation=3)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "component"):
                SeparationEngine(Path(folder) / "missing.json").separate("not-read.wav")
