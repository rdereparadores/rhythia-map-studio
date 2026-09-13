# Third-party notices

The project's `GPL-3.0-only` declaration applies to its original code. Dependencies, models and other third-party resources retain their own copyright notices and licenses.

## Main components

| Component | Use | Upstream reference |
| --- | --- | --- |
| Qt / PySide6 | Desktop interface and multimedia | [Qt licensing](https://doc.qt.io/qt-6/licensing.html) |
| NumPy | Numerical arrays | [NumPy license](https://github.com/numpy/numpy/blob/main/LICENSE.txt) |
| SciPy | Signal processing | [SciPy license](https://github.com/scipy/scipy/blob/main/LICENSE.txt) |
| SoundFile | Audio decoding and encoding | [SoundFile license](https://github.com/bastibe/python-soundfile/blob/master/LICENSE) |
| Demucs | Optional source separation | [Demucs license](https://github.com/facebookresearch/demucs/blob/main/LICENSE) |
| PyTorch / torchaudio | Optional separator runtime | [PyTorch license](https://github.com/pytorch/pytorch/blob/main/LICENSE) |

The optional model is `htdemucs`, used with Demucs 4.0.1. Its checkpoint and expected hash are specified in `tools/prepare_models.py`.

## Binary distributions

This document is an index, not a complete inventory of transitive dependencies or a substitute for their license texts. Review the exact components included in each binary build. Preserve their bundled notices and any accompanying `third-party-licenses` directory when redistributing them. The build script copies this index and the project license; those copies alone are not a complete dependency-license audit.

## Audio and maps

The project's code license does not grant redistribution rights to songs, community maps or other user-provided material. These are not included in the source repository or the source archive produced by `tools/source_archive.py`.
