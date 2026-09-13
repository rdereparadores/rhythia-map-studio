"""Release invariants: tag identity, complete assets and draft-only retries."""

import importlib.util
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {name: module}):
        spec.loader.exec_module(module)
    return module


version_tool = load_tool("release_version")
source_tool = load_tool("source_archive")
license_tool = load_tool("collect_licenses")
with patch.dict(sys.modules, {"release_version": version_tool, "source_archive": source_tool}):
    package_tool = load_tool("package_release")
    publish_tool = load_tool("publish_release")


class ReleaseTests(unittest.TestCase):
    def test_dependency_metadata_is_preserved_without_email_reserialization(self):
        distribution = Mock()
        distribution.metadata = {"Name": "example"}
        distribution.version = "1.0"
        distribution.files = []
        original = "Name: example\nVersion: 1.0\n\nDescription with original line breaks.\n"
        distribution.read_text.return_value = original
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            with patch.object(license_tool.metadata, "distributions", return_value=[distribution]):
                license_tool.collect(destination)
            self.assertEqual((destination / "example/METADATA.txt").read_text(), original)

    def test_release_candidate_maps_to_python_version(self):
        self.assertTrue(version_tool.validate_tag("v0.2.0-rc.1", "0.2.0rc1"))
        self.assertFalse(version_tool.validate_tag("v0.1.0", "0.1.0"))

    def test_bad_tags_and_mismatched_versions_fail(self):
        for tag, version in (
            ("v0.1.0", "0.2.0"),
            ("v01.1.0", "01.1.0"),
            ("v0.1.0-rc.0", "0.1.0rc0"),
            ("v0.1.0;echo bad", "0.1.0"),
            ("main", "0.1.0"),
        ):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                version_tool.validate_tag(tag, version)

    def test_archive_preserves_launcher_layout_and_excludes_separator(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            for name in ("Launch Map Studio.cmd", "bin/App/_internal/lib.dll", "separation/model.th"):
                path = staging / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"example")
            archive_path = root / "app.zip"
            package_tool.create_archive(staging, archive_path, exclude=("separation",))
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(
                    set(archive.namelist()), {"Launch Map Studio.cmd", "bin/App/_internal/lib.dll"}
                )

    def test_asset_size_limit_blocks_upload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            staging.mkdir()
            (staging / "file.txt").write_text("content")
            with patch.object(package_tool, "MAX_ASSET_BYTES", 1), self.assertRaises(ValueError):
                package_tool.create_archive(staging, root / "oversized.zip")

    def test_checksums_require_all_three_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            arguments = ["package_release.py", "checksums", "--output", str(root)]
            with patch.object(sys, "argv", arguments), self.assertRaises(ValueError):
                package_tool.main()
            version = version_tool.package_version()
            for suffix in ("windows-x64", "source", "separator-cpu-windows-x64"):
                (root / f"RhythiaMapStudio-{version}-{suffix}.zip").write_bytes(b"fixture")
            with patch.object(sys, "argv", arguments):
                package_tool.main()
            self.assertEqual(len((root / "SHA256SUMS.txt").read_text().splitlines()), 3)

    def test_published_release_is_never_overwritten(self):
        with (
            patch.dict(os.environ, {"RELEASE_TAG": "v0.1.0", "GITHUB_REPOSITORY": "owner/repo"}),
            patch.object(publish_tool, "package_version", return_value="0.1.0"),
            patch.object(publish_tool, "gh", return_value='[[{"tag_name":"v0.1.0","draft":false}]]') as gh,
            self.assertRaises(ValueError),
        ):
            publish_tool.main()
        self.assertEqual(gh.call_count, 1)

    def test_auto_publication_requires_explicit_repository_variable(self):
        for automatic in ("", "false", "true"):
            with (
                self.subTest(automatic=automatic),
                patch.dict(
                    os.environ,
                    {
                        "RELEASE_TAG": "v0.1.0",
                        "GITHUB_REPOSITORY": "owner/repo",
                        "RELEASE_AUTO_PUBLISH": automatic,
                    },
                ),
                patch.object(publish_tool, "package_version", return_value="0.1.0"),
                patch.object(publish_tool, "gh", side_effect=["[[]]", "", "", ""]) as gh,
            ):
                publish_tool.main()
                self.assertIn("--draft", gh.call_args_list[1].args)
                self.assertEqual("--draft=false" in gh.call_args_list[-1].args, automatic == "true")


if __name__ == "__main__":
    unittest.main()
