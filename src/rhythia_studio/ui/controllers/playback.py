"""Own media resources and synchronize playback with the preview."""

import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from ...messages import Message

if TYPE_CHECKING:
    from ..window import Studio


class PlaybackController(QObject):
    def __init__(self, window: "Studio"):
        super().__init__(window)
        self.window = window
        self.temp = tempfile.TemporaryDirectory(prefix="rhythia-studio-", ignore_cleanup_errors=True)
        self.audio_path = None
        self.player = QMediaPlayer(window)
        self.audio_out = QAudioOutput(window)
        self.audio_out.setVolume(0.65)
        self.player.setAudioOutput(self.audio_out)
        self.player.positionChanged.connect(self.position)
        self.player.playbackStateChanged.connect(self.playback_changed)
        self.player.errorOccurred.connect(
            lambda *args: window.show_status(Message("Audio: {detail}", detail=self.player.errorString()))
        )

    def load_audio(self, name: str, audio: bytes) -> None:
        """Stage new audio successfully before releasing the current media source."""
        suffix = Path(name).suffix.lower()
        if suffix not in (".mp3", ".wav", ".flac", ".ogg"):
            suffix = ".mp3"
        path = Path(self.temp.name) / (uuid.uuid4().hex + suffix)
        path.write_bytes(audio)
        self.player.stop()
        self.player.setSource(QUrl())
        self.audio_path = path
        self.player.setSource(QUrl.fromLocalFile(str(path)))

    def shutdown(self) -> None:
        self.player.stop()
        self.player.setSource(QUrl())

    def position(self, ms):
        window = self.window
        start, end = self.region()
        if (
            window.view.loop.isChecked()
            and end > start
            and ms >= end
            and self.player.playbackState() == QMediaPlayer.PlayingState
        ):
            self.player.setPosition(start)
            return
        if not window.view.slider.isSliderDown():
            window.view.slider.setValue(ms)
        window.view.grid.time = ms
        window.view.grid.update()
        window.view.timeline.set_position(ms)
        duration = window.document.project["analysis"]["duration_ms"] if window.document.project else 0
        window.view.clock.setText(
            f"{ms // 60000}:{ms // 1000 % 60:02d} / {duration // 60000}:{duration // 1000 % 60:02d}"
        )

    def seek(self, ms):
        self.player.setPosition(ms)
        self.position(ms)

    def playback_changed(self, state):
        window = self.window
        window.view.play_btn.setText(window.t("Pause" if state == QMediaPlayer.PlayingState else "Play"))

    def toggle_play(self):
        window = self.window
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            start, end = self.region()
            if window.view.loop.isChecked() and end > start and not start <= self.player.position() < end:
                self.seek(start)
            self.player.play()

    def region(self):
        window = self.window
        return round(window.view.range_start.value() * 1000), round(window.view.range_end.value() * 1000)

    def set_region(self, start, end):
        window = self.window
        window.view.range_start.blockSignals(True)
        window.view.range_end.blockSignals(True)
        window.view.range_start.setValue(start / 1000)
        window.view.range_end.setValue(end / 1000)
        window.view.range_start.blockSignals(False)
        window.view.range_end.blockSignals(False)
        self.range_changed()

    def range_changed(self, *args):
        window = self.window
        window.view.timeline.selection = self.region()
        window.view.timeline.update()
