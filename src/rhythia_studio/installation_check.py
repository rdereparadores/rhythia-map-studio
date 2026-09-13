"""Offline smoke check for a packaged installation, without opening Rhythia."""

import tempfile
from pathlib import Path

from .i18n import languages
from .ui.window import Studio


def check_installation(app) -> None:
    """Exercise packaged Qt, catalogs and assets without preferences or audio."""
    with tempfile.TemporaryDirectory(prefix="rhythia-check-") as directory:
        window = Studio(recovery_directory=directory, offer_recovery=False, persist_language=False)
        try:
            for language in languages():
                window.view.language.setCurrentIndex(window.view.language.findData(language))
                window.settings()
                window.view.advanced_toggle.setChecked(True)
                window.view.advanced_toggle.setChecked(False)
                app.processEvents()
            assets = Path(__file__).parent / "ui" / "assets"
            for name in ("check.svg", "down.svg", "plus.svg", "minus.svg"):
                if not (assets / name).is_file():
                    raise FileNotFoundError(assets / name)
        finally:
            window.close()
            app.processEvents()
