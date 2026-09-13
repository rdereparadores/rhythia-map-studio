# Publishing Windows releases

The `Release` GitHub Actions workflow runs when a `v*` tag is pushed. It validates
the tag, builds from that exact commit on Windows, and prepares a GitHub Release.
It does not publish on ordinary pushes or pull requests.

## One-time repository setup

1. Merge the release workflow and supporting files into `main`.
2. Enable GitHub Actions. Keep the default token permissions read-only; the final
   release job requests `contents: write` itself. No personal access token is needed.
3. Leave `RELEASE_AUTO_PUBLISH` unset for the first release. The workflow will create
   a draft with all downloads attached. No manual approval environment is required.
4. Optionally protect `v*` tags with a repository ruleset that blocks updates and
   deletion, and restricts creation to maintainers.

After downloading the first draft and testing it on a clean Windows machine, publish
it from **Releases → Edit draft → Publish release**. Verify startup, song import,
generation, playback, save/reopen, export and optional separation. Only the human
tester should launch Rhythia for the in-game check.

To publish subsequent releases automatically, open **Settings → Secrets and variables
→ Actions → Variables → New repository variable** and set:

```text
Name: RELEASE_AUTO_PUBLISH
Value: true
```

Unset it or set it to `false` to return to draft-only releases. This setting is a
repository variable, not a secret. If desired, enable release immutability under
**Settings → General → Releases**; all assets are attached before publication.

## Publish a version

1. Update `src/rhythia_studio/__init__.py`, `CHANGELOG.md` and
   `docs/RELEASE_NOTES.md` in a pull request. Review the pinned release requirements
   when dependencies change. Ensure the ordinary `Checks` workflow passes.
2. Merge the pull request into `main` and check out the resulting commit locally.
3. Create and push a matching tag, for example:

   ```powershell
   git switch main
   git pull --ff-only
   git tag -a v0.1.0 -m "Release 0.1.0"
   git push origin v0.1.0
   ```

4. Follow **Actions → Release**. Failed checks prevent release publication.

Use a new version for each published release; do not move or reuse a published tag.
For a candidate, use package version `0.2.0rc1` and tag `v0.2.0-rc.1`. Candidate tags
produce pre-releases and are not marked latest. Stable tags use `vMAJOR.MINOR.PATCH`.

## What the workflow does

- Confirms the package version matches the tag and the tagged commit belongs to `main`.
- Installs pinned Windows/Python 3.12 release dependencies in separate jobs.
- Runs style checks and the test suite against the release commit.
- Compiles the application and runs its offscreen installation check from a temporary directory.
- Compiles the CPU separator, verifies the pinned model and separates synthetic audio.
- Preserves installed dependency license files and metadata, and records the build environment.
- Produces separate application, CPU separator and source ZIPs plus `SHA256SUMS.txt`.
- Rejects assets at or above GitHub's 2 GiB per-file limit.
- Uploads all assets to a draft, then publishes only if `RELEASE_AUTO_PUBLISH` is `true`.

The downloadable ZIPs have matching layouts: extract the separator into the app's
folder to enable it. CUDA packages are not produced by this workflow. Developers
can still use the CUDA build instructions in [BUILDING.md](BUILDING.md).

Pins capture the Python dependencies, but the hosted runner, Python patch version
and upstream build tools may still change. Byte-for-byte reproducibility is not
claimed. Dependency metadata collection preserves available license texts; review
the actual binary distribution and its notices when changing dependencies.

## Failures and retries

Open the failed job's log and fix the cause. Re-run failed jobs for transient failures;
source or dependency fixes require a new commit and tag. A retry may update an
existing **draft** for the same tag, but refuses to overwrite any published release.
App and separator artifacts remain downloadable from the workflow for 14 days.

The workflow never changes repository settings, pushes commits, or launches Rhythia.
