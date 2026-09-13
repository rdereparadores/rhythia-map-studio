"""Widget construction and styling, separated from document operations."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..i18n import languages
from ..models import LEVELS
from ..separation import available
from .theme import OUTER_SPACE, PANEL_SPACE, SPACE, stylesheet
from .view import StudioView
from .widgets import Grid, Timeline


def button(text, callback, primary=False):
    result = QPushButton(text)
    result.clicked.connect(callback)
    if primary:
        result.setObjectName("primary")
    return result


def table(labels):
    result = QTableWidget(0, len(labels))
    result.setHorizontalHeaderLabels(labels)
    result.setSelectionBehavior(QAbstractItemView.SelectRows)
    result.setEditTriggers(QAbstractItemView.NoEditTriggers)
    result.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    result.verticalHeader().hide()
    result.verticalHeader().setDefaultSectionSize(34)
    result.setShowGrid(False)
    result.setAlternatingRowColors(True)
    return result


def section(text):
    label = QLabel(text)
    label.setObjectName("section")
    return label


def muted(text):
    result = QLabel(text)
    result.setObjectName("muted")
    result.setWordWrap(True)
    return result


def build_ui(window, view: StudioView):
    root = QWidget()
    root.setObjectName("canvas")
    window.setCentralWidget(root)
    layout = QVBoxLayout(root)
    layout.setContentsMargins(OUTER_SPACE, OUTER_SPACE, OUTER_SPACE, SPACE)
    layout.setSpacing(SPACE)
    _build_header(window, view, layout)
    body = QHBoxLayout()
    body.setSpacing(PANEL_SPACE)
    _build_song_panel(window, view, body)
    _build_preview(window, view, body)
    layout.addLayout(body, 1)
    view.advanced_widgets = (view.advanced_settings, view.tabs, view.timeline, view.range_controls, view.rate)
    view.separate_audio.toggled.connect(window.update_priority_controls)
    window.update_priority_controls()
    window.set_advanced(False)
    window.setStyleSheet(stylesheet())


def _build_editor(window, view, split):
    view.tabs = QTabWidget()
    view.tabs.setMinimumWidth(320)
    edit = QWidget()
    edit_layout = QVBoxLayout(edit)
    edit_layout.setContentsMargins(0, 0, 0, 0)
    edit_layout.setSpacing(SPACE)
    view.table = table(["Time · s", "X", "Y", "Lead"])
    view.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    view.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    view.table.itemSelectionChanged.connect(window.editor.select_note)
    edit_layout.addWidget(view.table)
    view.note_time = QDoubleSpinBox()
    view.note_time.setDecimals(3)
    view.note_time.setRange(0, 1200)
    view.note_time.setSuffix(" s")
    edit_layout.addWidget(view.note_time)
    edit_layout.addWidget(button("Move selection to this time", window.editor.retime))
    row = QHBoxLayout()
    row.addWidget(button("Add", window.editor.add_note))
    row.addWidget(button("Delete", window.editor.delete_note))
    edit_layout.addLayout(row)
    row = QHBoxLayout()
    row.addWidget(button("Undo", window.editor.undo))
    row.addWidget(button("Redo", window.editor.redo))
    edit_layout.addLayout(row)
    view.tabs.addTab(edit, "Notes")
    view.sections_table = table(["Group", "Start", "Duration", "Section similarity"])
    view.sections_table.setSelectionMode(QAbstractItemView.SingleSelection)
    view.sections_table.itemSelectionChanged.connect(window.editor.select_section)
    view.tabs.addTab(view.sections_table, "Sections")
    view.phrases_table = table(["Start", "Lead", "Role", "Intensity"])
    view.phrases_table.setSelectionMode(QAbstractItemView.SingleSelection)
    view.phrases_table.itemSelectionChanged.connect(window.editor.select_phrase)
    view.tabs.addTab(view.phrases_table, "Phrases")
    view.issues = table(["Time", "Review"])
    view.issues.itemSelectionChanged.connect(window.editor.select_issue)
    view.tabs.addTab(view.issues, "Review")
    split.addWidget(view.tabs)


def _build_transport(window, view, right):
    transport = QHBoxLayout()
    transport.setSpacing(SPACE)
    view.play_btn = button("Play", window.playback.toggle_play)
    view.play_btn.setProperty("dynamicText", True)
    transport.addWidget(view.play_btn)
    view.slider = QSlider(Qt.Horizontal)
    view.slider.sliderMoved.connect(window.playback.seek)
    transport.addWidget(view.slider, 1)
    view.rate = QComboBox()
    for label, rate in zip(("0.5×", "0.75×", "1×", "1.25×"), (0.5, 0.75, 1, 1.25), strict=True):
        view.rate.addItem(label, rate)
    view.rate.setCurrentIndex(2)
    view.rate.currentIndexChanged.connect(
        lambda: window.playback.player.setPlaybackRate(view.rate.currentData())
    )
    transport.addWidget(view.rate)
    view.clock = QLabel("0:00 / 0:00")
    view.clock.setProperty("dynamicText", True)
    transport.addWidget(view.clock)
    view.transport = QWidget()
    view.transport.setLayout(transport)
    transport.setContentsMargins(0, 0, 0, 0)
    right.addWidget(view.transport)


def _build_preview(window, view, body):
    right = QVBoxLayout()
    right.setSpacing(SPACE)
    view.preview_title = QLabel("Your map starts with a song")
    view.preview_title.setProperty("dynamicText", True)
    view.preview_title.setObjectName("heading")
    view.preview_title.setWordWrap(True)
    right.addWidget(view.preview_title)
    view.stats = muted("No map")
    view.stats.setProperty("dynamicText", True)
    right.addWidget(view.stats)
    split = QSplitter()
    split.setHandleWidth(PANEL_SPACE)
    split.setChildrenCollapsible(False)
    view.preview = split
    grid_container = QWidget()
    grid_layout = QVBoxLayout(grid_container)
    grid_layout.setContentsMargins(0, 0, 0, 0)
    view.grid = Grid()
    view.grid.moved.connect(window.editor.move_note)
    grid_layout.addWidget(view.grid, 1)
    view.preview_hint = muted("Listen and preview your map before exporting.")
    view.preview_hint.setProperty("dynamicText", True)
    grid_layout.addWidget(view.preview_hint)
    split.addWidget(grid_container)
    _build_editor(window, view, split)
    split.setSizes([480, 360])
    right.addWidget(split, 1)
    view.empty_state = muted("Your preview will appear once you generate a map.")
    view.empty_state.setAlignment(Qt.AlignCenter)
    right.addWidget(view.empty_state, 1)
    view.timeline = Timeline()
    view.timeline.seek.connect(window.playback.seek)
    view.timeline.range_selected.connect(window.playback.set_region)
    view.timeline.note_dragged.connect(window.editor.drag_note)
    right.addWidget(view.timeline)
    ranges = QHBoxLayout()
    view.range_start = QDoubleSpinBox()
    view.range_end = QDoubleSpinBox()
    for control in (view.range_start, view.range_end):
        control.setDecimals(3)
        control.setRange(0, 1200)
        control.setSuffix(" s")
        control.valueChanged.connect(window.playback.range_changed)
    ranges.addWidget(QLabel("Range"))
    ranges.addWidget(view.range_start)
    ranges.addWidget(view.range_end)
    view.loop = QCheckBox("Loop")
    ranges.addWidget(view.loop)
    ranges.addStretch()
    ranges.addWidget(button("−", lambda: view.timeline.zoom(1.5)))
    ranges.addWidget(button("+", lambda: view.timeline.zoom(1 / 1.5)))
    ranges.addWidget(button("All", view.timeline.show_all))
    view.range_controls = QWidget()
    view.range_controls.setLayout(ranges)
    ranges.setContentsMargins(0, SPACE, 0, SPACE)
    ranges.setSpacing(SPACE)
    right.addWidget(view.range_controls)
    _build_transport(window, view, right)
    body.addLayout(right, 1)


def _space_forms(*forms):
    for form_layout in forms:
        form_layout.setHorizontalSpacing(SPACE)
        form_layout.setVerticalSpacing(SPACE)
        form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)


def _build_advanced_settings(window, view, left):
    view.advanced_settings = QWidget()
    advanced = QVBoxLayout(view.advanced_settings)
    advanced.setContentsMargins(0, SPACE, 0, 0)
    advanced.setSpacing(PANEL_SPACE)
    advanced.addWidget(section("GENERATION"))
    form = QFormLayout()
    view.generation_form = form
    view.mix_emphasis = QComboBox()
    for label, value in (("Automatic", "Mix"), ("Percussive", "Percussion"), ("Tonal", "Tonal")):
        view.mix_emphasis.addItem(label, value)
    view.mix_emphasis.setToolTip(
        "Guide the analysis of the mix; this does not isolate vocals or instruments."
    )
    form.addRow("Mix\nanalysis", view.mix_emphasis)
    view.bpm = QDoubleSpinBox()
    view.bpm.setRange(0, 300)
    view.bpm.setDecimals(3)
    view.bpm.setSpecialValueText("Automatic tempo")
    form.addRow("BPM", view.bpm)
    tempo_buttons = QHBoxLayout()
    tempo_buttons.setSpacing(4)
    tempo_buttons.addWidget(button("½", lambda: window.scale_tempo(0.5)))
    tempo_buttons.addWidget(button("×2", lambda: window.scale_tempo(2)))
    tempo_buttons.addWidget(button("Auto", lambda: view.bpm.setValue(0)))
    form.addRow("", tempo_buttons)
    view.variable = QCheckBox("Variable tempo (experimental)")
    form.addRow(view.variable)
    view.density = QDoubleSpinBox()
    view.density.setRange(0.5, 1.5)
    view.density.setSingleStep(0.1)
    view.density.setValue(1)
    form.addRow("Density", view.density)
    view.offset = QSpinBox()
    view.offset.setRange(-2000, 2000)
    view.offset.setSuffix(" ms")
    form.addRow("Offset", view.offset)
    view.style = QComboBox()
    for style in ("Flowing", "Jumps"):
        view.style.addItem(style, style)
    form.addRow("Movement", view.style)
    view.seed = QSpinBox()
    view.seed.setRange(0, 999999)
    view.seed.setValue(42)
    form.addRow("Seed", view.seed)
    view.variation = QDoubleSpinBox()
    view.variation.setRange(0, 2)
    view.variation.setSingleStep(0.25)
    view.variation.setValue(1)
    view.variation.setToolTip(
        "Strength of repetition control within phrases. Similar sections still share their design."
    )
    form.addRow("Variation", view.variation)
    advanced.addLayout(form)
    advanced.addWidget(section("REPETITION"))
    view.repeat = QCheckBox("Patterns in similar sections")
    view.repeat.setChecked(True)
    advanced.addWidget(view.repeat)
    similarity_form = QFormLayout()
    view.similarity = QDoubleSpinBox()
    view.similarity.setRange(0.5, 0.98)
    view.similarity.setSingleStep(0.02)
    view.similarity.setValue(0.78)
    similarity_form.addRow("Similarity", view.similarity)
    advanced.addLayout(similarity_form)
    advanced.addWidget(
        muted("A higher threshold requires a closer match. R1, R2… group acoustically similar phrases.")
    )
    view.preserve = QCheckBox("Keep edits when regenerating")
    view.preserve.setChecked(True)
    advanced.addWidget(view.preserve)
    view.region_btn = button("Regenerate selection only", window.generation.regenerate_region)
    advanced.addWidget(view.region_btn)
    advanced.addWidget(muted("Select a range in Sections or Shift-drag on the timeline."))
    advanced.addWidget(section("PROJECT"))
    view.title_edit = QLineEdit()
    view.title_edit.setPlaceholderText("Map title")
    view.title_edit.textEdited.connect(window.documents.change_title)
    advanced.addWidget(view.title_edit)
    advanced.addWidget(view.recover_btn)
    _space_forms(form, similarity_form)
    left.addWidget(view.advanced_settings)


def _build_song_panel(window, view, body):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFixedWidth(320)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.NoFrame)
    panel = QFrame()
    panel.setObjectName("panel")
    scroll.setWidget(panel)
    left = QVBoxLayout(panel)
    left.setSpacing(PANEL_SPACE)
    left.setContentsMargins(PANEL_SPACE, PANEL_SPACE, PANEL_SPACE, PANEL_SPACE)
    left.addWidget(section("SONG"))
    view.song = muted("Choose a song to get started")
    view.song.setProperty("dynamicText", True)
    left.addWidget(view.song)
    view.import_btn = button("Choose song…", window.documents.import_audio)
    left.addWidget(view.import_btn)
    view.separate_audio = QCheckBox("Separate vocals and instruments")
    view.separate_audio.setChecked(available())
    view.separate_audio.setToolTip(
        "Separate four tracks locally and choose the lead for each phrase. Tracks are cached; the map keeps the original audio."
    )
    left.addWidget(view.separate_audio)
    basic = QFormLayout()
    view.basic_form = basic
    basic.setSpacing(12)
    view.level = QComboBox()
    for level in LEVELS:
        view.level.addItem(level, level)
    view.level.setCurrentText("Normal")
    view.level.currentTextChanged.connect(window.refresh)
    basic.addRow("Difficulty", view.level)
    view.emphasis = QComboBox()
    view.emphasis.addItems(["Mix", "Percussion", "Tonal", "Vocals"])
    basic.addRow("Priority", view.emphasis)
    view.emphasis.setItemText(0, "Automatic")
    view.emphasis.setItemData(0, "Mix")
    for i in range(1, view.emphasis.count()):
        view.emphasis.setItemData(i, view.emphasis.itemText(i))
    left.addLayout(basic)
    left.addWidget(muted("Rhythm and patterns are adjusted automatically."))
    view.generate_btn = button("Generate map", window.generation.regenerate, True)
    view.generate_btn.setProperty("dynamicText", True)
    left.addWidget(view.generate_btn)
    view.cancel_btn = button("Cancel analysis", window.generation.cancel_generation)
    view.cancel_btn.hide()
    left.addWidget(view.cancel_btn)
    view.progress = QProgressBar()
    view.progress.setRange(0, 0)
    view.progress.hide()
    left.addWidget(view.progress)
    view.advanced_toggle = QPushButton("Advanced options")
    view.advanced_toggle.setProperty("dynamicText", True)
    view.advanced_toggle.setCheckable(True)
    view.advanced_toggle.toggled.connect(window.set_advanced)
    left.addWidget(view.advanced_toggle)
    _build_advanced_settings(window, view, left)
    _space_forms(basic)
    left.addStretch()
    body.addWidget(scroll)


def _build_header(window, view, layout):
    header = QHBoxLayout()
    header.setSpacing(SPACE)
    heading = QLabel("Rhythia Map Studio")
    heading.setObjectName("heading")
    header.addWidget(heading)
    header.addStretch()
    header.addWidget(QLabel("Language"))
    view.language = QComboBox()
    for code, name in languages().items():
        view.language.addItem(name, code)
    view.language.setCurrentIndex(view.language.findData(window.translator.language))
    view.language.currentIndexChanged.connect(window.change_language)
    header.addWidget(view.language)
    view.open_btn = button("Open", window.documents.open_project)
    view.save_btn = button("Save", window.documents.save)
    view.recover_btn = button("Recover", window.documents.recover)
    view.export_btn = button("Export .rhm", window.documents.export, True)
    for b in (view.open_btn, view.save_btn, view.export_btn):
        header.addWidget(b)
    layout.addLayout(header)
    layout.addWidget(muted("Choose your song. Create your map. Play your way."))
