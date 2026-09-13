"""Explicit widget references shared by the builders and controllers."""

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTabWidget,
    QWidget,
)

from .widgets import Grid, Timeline


@dataclass(init=False)
class StudioView:
    advanced_settings: QWidget
    advanced_toggle: QPushButton
    advanced_widgets: tuple[QWidget, ...]
    basic_form: QFormLayout
    bpm: QDoubleSpinBox
    cancel_btn: QPushButton
    clock: QLabel
    density: QDoubleSpinBox
    emphasis: QComboBox
    empty_state: QLabel
    export_btn: QPushButton
    generate_btn: QPushButton
    generation_form: QFormLayout
    grid: Grid
    import_btn: QPushButton
    issues: QTableWidget
    language: QComboBox
    level: QComboBox
    loop: QCheckBox
    mix_emphasis: QComboBox
    note_time: QDoubleSpinBox
    offset: QSpinBox
    open_btn: QPushButton
    phrases_table: QTableWidget
    play_btn: QPushButton
    preserve: QCheckBox
    preview: QSplitter
    preview_hint: QLabel
    preview_title: QLabel
    progress: QProgressBar
    range_controls: QWidget
    range_end: QDoubleSpinBox
    range_start: QDoubleSpinBox
    rate: QComboBox
    recover_btn: QPushButton
    region_btn: QPushButton
    repeat: QCheckBox
    save_btn: QPushButton
    sections_table: QTableWidget
    seed: QSpinBox
    separate_audio: QCheckBox
    similarity: QDoubleSpinBox
    slider: QSlider
    song: QLabel
    stats: QLabel
    style: QComboBox
    table: QTableWidget
    tabs: QTabWidget
    timeline: Timeline
    title_edit: QLineEdit
    transport: QWidget
    variable: QCheckBox
    variation: QDoubleSpinBox
