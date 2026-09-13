"""Application entry point; installs a readable log and startup error handler."""

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from .ui.window import Studio


def main():
    installation_check = "--check-installation" in sys.argv
    if installation_check:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    app.setApplicationName("RhythiaMapStudio")
    app.setOrganizationName("LocalTools")
    if installation_check:
        from .installation_check import check_installation

        check_installation(app)
        return 0
    data = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    data.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=data / "studio.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    def exception_hook(kind, value, traceback):
        logging.error("Unhandled error", exc_info=(kind, value, traceback))
        QMessageBox.critical(
            None,
            "Rhythia Map Studio",
            window.t(
                "An error occurred: {error}\nLog: {path}",
                error=window.t(value),
                path=data / "studio.log",
            ),
        )

    path = sys.argv[1] if len(sys.argv) > 1 else None
    window = Studio(path)
    sys.excepthook = exception_hook
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
