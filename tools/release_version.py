"""Validate release tags against the package version and Git history."""

import ast
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG_PATTERN = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-rc\.([1-9]\d*))?")


def package_version():
    module = ast.parse((ROOT / "src/rhythia_studio/__init__.py").read_text(encoding="utf-8"))
    for statement in module.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__" for target in statement.targets
        ):
            return ast.literal_eval(statement.value)
    raise ValueError("Package version is missing.")


def validate_tag(tag, version):
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError("Use vMAJOR.MINOR.PATCH or vMAJOR.MINOR.PATCH-rc.N.")
    expected = ".".join(match.group(1, 2, 3))
    if match[4]:
        expected += "rc" + match[4]
    if version != expected:
        raise ValueError(f"Tag {tag} requires package version {expected}, found {version}.")
    return match[4] is not None


def main():
    tag = os.environ["RELEASE_TAG"]
    version = package_version()
    prerelease = validate_tag(tag, version)
    subprocess.run(["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"], cwd=ROOT, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tagged = subprocess.check_output(
        ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], cwd=ROOT, text=True
    ).strip()
    if commit != tagged:
        raise ValueError("The checked-out commit does not match the release tag.")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"version={version}\nprerelease={str(prerelease).lower()}\ncommit={commit}\n")


if __name__ == "__main__":
    main()
