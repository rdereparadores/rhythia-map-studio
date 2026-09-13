"""Render the empty, basic and expanded UI without playing audio."""

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from rhythia_studio.ui.window import Studio


def main():
    project, destination = Path(sys.argv[1]), Path(sys.argv[2])
    destination.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    font = Path("C:/Windows/Fonts/segoeui.ttf")
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
    window = Studio(
        recovery_directory=destination / "recovery",
        offer_recovery=False,
        language="en" if "--english" in sys.argv[3:] else "es",
        persist_language=False,
    )
    if "--compact" in sys.argv[3:]:
        window.resize(1040, 800)
    window.playback.audio_out.setVolume(0)
    window.show()
    app.processEvents()
    window.grab().save(str(destination / "inicio.png"))
    window.documents.read_project(project)
    if "--mixed" in sys.argv[3:]:
        window.view.separate_audio.setChecked(False)
    app.processEvents()
    window.grab().save(str(destination / "basica.png"))
    window.view.advanced_toggle.click()
    app.processEvents()
    window.grab().save(str(destination / "avanzada.png"))
    window.set_dirty(False)
    window.close()
    app.processEvents()


if __name__ == "__main__":
    main()
