"""Attach complete assets to a draft; publish only when explicitly enabled."""

import json
import os
import subprocess
from pathlib import Path

from release_version import package_version, validate_tag


def gh(*arguments):
    return subprocess.check_output(["gh", *arguments], text=True).strip()


def main():
    tag = os.environ["RELEASE_TAG"]
    prerelease = validate_tag(tag, package_version())
    repository = os.environ["GITHUB_REPOSITORY"]
    # A successful API request distinguishes an absent release from authentication/network errors.
    pages = json.loads(gh("api", "--paginate", "--slurp", f"repos/{repository}/releases?per_page=100"))
    existing = next((release for page in pages for release in page if release["tag_name"] == tag), None)
    if existing and not existing["draft"]:
        raise ValueError("This tag already has a published release. Create a new version instead.")
    if not existing:
        gh(
            "release",
            "create",
            tag,
            "--verify-tag",
            "--draft",
            "--title",
            f"Rhythia Map Studio {tag}",
            "--notes-file",
            "docs/RELEASE_NOTES.md",
        )

    folder = Path("release-assets")
    expected_names = {path.name for path in folder.glob("*.zip")} | {"SHA256SUMS.txt"}
    # Remove obsolete assets only from an unpublished draft when retrying the same tag.
    if existing:
        for asset in existing["assets"]:
            if asset["name"] not in expected_names:
                gh("release", "delete-asset", tag, asset["name"], "--yes")
    gh("release", "upload", tag, *[str(folder / name) for name in sorted(expected_names)], "--clobber")
    notes = Path("docs/RELEASE_NOTES.md")
    arguments = [
        "release",
        "edit",
        tag,
        "--notes-file",
        str(notes),
        f"--prerelease={str(prerelease).lower()}",
    ]
    if os.environ.get("RELEASE_AUTO_PUBLISH") == "true":
        arguments.extend(["--draft=false", f"--latest={str(not prerelease).lower()}"])
    gh(*arguments)
    print("Release published." if "--draft=false" in arguments else "Release ready as a draft.")


if __name__ == "__main__":
    main()
