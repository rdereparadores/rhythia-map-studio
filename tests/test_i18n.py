import json
import tempfile
import unittest
from pathlib import Path
from string import Formatter

from rhythia_studio.i18n import CATALOGS, Translator
from rhythia_studio.messages import Message


class TranslationTests(unittest.TestCase):
    def test_catalogs_have_matching_keys_and_placeholders(self):
        catalogs = [
            json.loads(path.read_text(encoding="utf-8"))["messages"] for path in CATALOGS.glob("*.json")
        ]
        self.assertGreater(len(catalogs[0]), 100)
        for catalog in catalogs:
            self.assertEqual(set(catalog), set(catalogs[0]))
            for source, target in catalog.items():
                source_fields = {f for _, f, _, _ in Formatter().parse(source) if f}
                target_fields = {f for _, f, _, _ in Formatter().parse(target) if f}
                self.assertEqual(source_fields, target_fields, source)

    def test_formatted_messages_preserve_user_data_and_fallback(self):
        t = Translator("en")
        self.assertEqual(
            t.text(Message("The {source} track is not aligned with the song.", source="vocals")),
            "The vocals track is not aligned with the song.",
        )
        path = "C:/Songs/Save {my song}.rmapproj"
        self.assertEqual(t.text("Project saved: {detail}", detail=path), "Project saved: " + path)
        self.assertEqual(t.text("future message"), "future message")
        self.assertEqual(Translator("../../missing").language, "en")
        self.assertEqual(
            t.text("{level} · {count} notes · Ready to export", level="Easy", count=20),
            "Easy · 20 notes · Ready to export",
        )

    def test_additional_catalog_requires_no_code_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "en.json").write_text(json.dumps(dict(name="English", messages={})), encoding="utf-8")
            (root / "fr.json").write_text(
                json.dumps(dict(name="Français", messages={"Save": "Enregistrer"})), encoding="utf-8"
            )
            self.assertEqual(Translator("fr", root).text("Save"), "Enregistrer")
