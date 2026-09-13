"""Workers return results through signals; they never touch widgets."""

import logging
from threading import Event

from PySide6.QtCore import QThread, Signal

from ..models import Cancelled

logger = logging.getLogger(__name__)


class GenerationWorker(QThread):
    progress = Signal(object)
    done = Signal(object, object)
    failed = Signal(object)
    cancelled = Signal(object)

    def __init__(self, service, path, settings, parent=None):
        super().__init__(parent)
        self.service, self.path, self.settings = service, path, settings
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            project, audio = self.service.create(
                self.path, self.settings, self.progress.emit, self.cancel_event.is_set
            )
            self.done.emit(project, audio)
        except Cancelled as ex:
            self.cancelled.emit(ex)
        except Exception as ex:
            logger.exception("Map generation failed")
            self.failed.emit(ex)


class SaveWorker(QThread):
    failed = Signal(object)

    def __init__(self, store, project, audio, parent=None):
        super().__init__(parent)
        self.store, self.project, self.audio = store, project, audio

    def run(self):
        try:
            self.store.save(self.project, self.audio)
        except Exception as ex:
            logger.exception("Project autosave failed")
            self.failed.emit(ex)
