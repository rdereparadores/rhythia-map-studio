# Rhythia Map Studio

A local Windows desktop app for generating and editing **Rhythia Steam** maps from music. Choose a song, set a difficulty and generate a map, then preview, edit and export it as `.rhm`.

The project is in early development. Generated maps are starting points for human review; timing estimates and playability diagnostics are not official Rhythia ratings.

## Features

- Generate Easy, Normal and Hard maps in one analysis pass.
- Reuse recognizable patterns across acoustically similar sections.
- Optionally separate vocals, drums, bass and other instruments with a local Demucs backend.
- Follow a musical lead automatically, or prioritize vocals, percussion or tonal content.
- Preview the map with audio playback and edit notes or selected regions with undo/redo.
- Save portable projects with embedded audio, autosave and recovery.
- Switch between English and Spanish without restarting.

Audio processing runs locally. Installing dependencies and downloading the optional model require an Internet connection; generating maps does not once the required components are installed.

## Requirements

| Component | Requirement |
| --- | --- |
| Desktop platform | Windows |
| Source installation | Python 3.11 or newer; Python 3.12 is the documented setup |
| Audio input | MP3, WAV, FLAC or OGG; 3 seconds to 20 minutes; up to 250 MB |
| Source separation | Optional backend and model; GPU acceleration when CUDA is available, otherwise CPU |

The desktop app uses PySide6/Qt. NumPy, SciPy and SoundFile provide audio analysis. The optional separator runs in its own process and Python environment.

## Install from source

Clone or download this repository, open PowerShell in its root directory, then run:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python run_studio.py
```

This installs the app without the optional source separator. See the [build and separator guide](docs/BUILDING.md) to add it or create a portable executable.

To open an existing project:

```powershell
.venv\Scripts\python run_studio.py "path\to\song.rmapproj"
```

The root launcher, `Launch Map Studio.cmd`, opens a local build under `dist` if present, or uses `.venv` otherwise. It is a convenience launcher, not an installer.

## Create a map

1. Choose a song. Analysis starts only when you click **Generate map**.
2. Choose the difficulty. Enable **Separate vocals and instruments** if the optional backend is installed.
3. With separation enabled, choose a **Priority**. **Automatic** selects the musical lead for each phrase.
4. Generate the map, then listen and review the preview. Other difficulties remain available without analyzing the song again.
5. Use **Save** to keep an editable project, or **Export .rhm** to export the selected difficulty.
6. In Rhythia Steam, use **Settings → Import Files** to import the exported map.

The app does not launch Rhythia or import maps into the game automatically.

**Advanced options** exposes tempo, density, timing offset, movement style, variation, repeated-section settings and the full editor. Closing it preserves generation settings, clears note selection and restores full-song playback at normal speed.

When separation is disabled, the Priority field is hidden. Advanced options offers a mixed-audio orientation instead; it weights percussive or tonal content without isolating instruments.

## File formats

| Extension | Purpose |
| --- | --- |
| `.rmapproj` | Editable project containing analysis, settings, all difficulty maps and the original audio |
| `.rhm` | Rhythia map containing the selected difficulty and original audio |

Save asks for a destination the first time and updates that file on subsequent saves. Version 0.1.0 uses project schema v1 with English internal identifiers. Only the current project format is supported. Audio is preserved without recompression.

## Limitations

- Tempo detection can select half or double the intended tempo. Manual correction is available; variable tempo remains experimental.
- Similarity groups such as R1 and R2 describe acoustic resemblance, not semantic chorus labels. General time-signature recognition is not implemented; structural analysis assumes a provisional 4/4 grid.
- Source separation can leak sound between stems. Pitch estimates guide movement but are not a musical transcription.
- Automated checks cover technical behavior, not musical quality. Review synchronization and comfort by playing the exported map.

## Development and contributions

Contributions to mapping, analysis, accessibility, translations and documentation are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) for setup, issue reports and pull requests.

| Document | Contents |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | Modules, data flow and invariants |
| [Build guide](docs/BUILDING.md) | Portable builds, optional separator and packaging checks |
| [Internationalization](I18N.md) | Translation catalogs and adding languages |
| [Changelog](CHANGELOG.md) | Version history |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | Dependency references and distribution notices |

## License

Original project code is licensed under **GNU GPL version 3 only** (`GPL-3.0-only`). See [LICENSE](LICENSE). Third-party components retain their own licenses. Songs and community maps are not covered by the project's code license.
