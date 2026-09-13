"""Shared visual tokens and Qt control states for the desktop interface."""

from pathlib import Path

SPACE = 8
PANEL_SPACE = 16
OUTER_SPACE = 24


def stylesheet():
    assets = (Path(__file__).parent / "assets").as_posix()
    return """
QWidget {color:#e5ebf5;font-family:"Segoe UI";font-size:13px;background:transparent;}
QMainWindow,QWidget#canvas {background:#0d1523;}
QLabel#heading {font-size:21px;font-weight:600;}
QLabel#muted {color:#9badc5;font-size:12px;}
QLabel#section {color:#aabbd0;font-size:11px;font-weight:600;padding-top:8px;}
QFrame#panel {background:#152136;border:1px solid #2c3d55;border-radius:12px;}
QPushButton {background:#23364d;border:1px solid #3b506a;border-radius:8px;padding:8px 12px;min-height:18px;}
QPushButton:hover {background:#2b425c;border-color:#62809c;}
QPushButton:pressed,QPushButton:checked {background:#1d4248;border-color:#76e6cd;}
QPushButton:focus {border-color:#76e6cd;}
QPushButton:disabled {color:#77889f;background:#182538;border-color:#2c3d55;}
QPushButton#primary {background:#76e6cd;color:#092c2b;border:1px solid #76e6cd;font-weight:600;}
QPushButton#primary:hover {background:#95eedb;border-color:#95eedb;}
QPushButton#primary:pressed {background:#53cbb2;border-color:#53cbb2;}
QPushButton#primary:disabled {background:#294e4d;color:#91aaa9;border-color:#294e4d;}
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox {background:#101c2d;border:1px solid #3b506a;border-radius:8px;padding:8px;min-height:18px;selection-background-color:#30586a;}
QLineEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus,QComboBox:focus {border-color:#76e6cd;}
QLineEdit:hover,QSpinBox:hover,QDoubleSpinBox:hover,QComboBox:hover {border-color:#62809c;}
QLineEdit:disabled,QSpinBox:disabled,QDoubleSpinBox:disabled,QComboBox:disabled {color:#77889f;border-color:#2c3d55;background:#182538;}
QComboBox {padding-right:28px;}
QComboBox::drop-down {subcontrol-origin:padding;subcontrol-position:top right;width:26px;border:0;}
QComboBox::down-arrow {image:url(ASSETS/down.svg);width:10px;height:10px;}
QComboBox QAbstractItemView {background:#152136;border:1px solid #3b506a;selection-background-color:#30586a;padding:4px;outline:0;}
QAbstractSpinBox {padding-right:26px;}
QSpinBox::up-button,QDoubleSpinBox::up-button {subcontrol-origin:border;subcontrol-position:top right;width:24px;height:18px;border:0;}
QSpinBox::down-button,QDoubleSpinBox::down-button {subcontrol-origin:border;subcontrol-position:bottom right;width:24px;height:18px;border:0;}
QSpinBox::up-arrow,QDoubleSpinBox::up-arrow {image:url(ASSETS/plus.svg);width:8px;height:8px;}
QSpinBox::down-arrow,QDoubleSpinBox::down-arrow {image:url(ASSETS/minus.svg);width:8px;height:8px;}
QCheckBox {spacing:8px;min-height:24px;}
QCheckBox::indicator {width:16px;height:16px;border:1px solid #62809c;border-radius:4px;background:#101c2d;}
QCheckBox::indicator:hover {border-color:#76e6cd;}
QCheckBox::indicator:checked {background:#76e6cd;border-color:#76e6cd;image:url(ASSETS/check.svg);}
QCheckBox:focus {color:#a4f2e1;}
QCheckBox:disabled {color:#77889f;}
QCheckBox::indicator:disabled {border-color:#3b506a;background:#294e4d;}
QTableWidget {background:#101c2d;alternate-background-color:#142237;border:1px solid #2c3d55;border-radius:8px;selection-background-color:#30586a;outline:0;}
QTableWidget::item {padding:6px;}
QTableWidget::item:selected {background:#30586a;color:#ffffff;}
QHeaderView::section {background:#1c2c42;padding:8px;border:0;border-bottom:1px solid #2c3d55;color:#b8c7db;}
QTabWidget::pane {border:1px solid #2c3d55;border-radius:8px;background:#111d30;padding:8px;}
QTabBar::tab {background:#19283d;border:1px solid transparent;border-top-left-radius:8px;border-top-right-radius:8px;padding:8px 10px;margin-right:4px;color:#aabbd0;}
QTabBar::tab:selected {background:#23404c;border-color:#3b5967;color:#e5ebf5;}
QTabBar::tab:hover {color:#ffffff;background:#253b51;}
QScrollArea {border:0;}
QScrollBar:vertical {background:transparent;width:10px;margin:4px 0;}
QScrollBar::handle:vertical {background:#3b506a;border-radius:4px;min-height:28px;}
QScrollBar::handle:vertical:hover {background:#62809c;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QScrollBar:horizontal {background:transparent;height:10px;}
QScrollBar::handle:horizontal {background:#3b506a;border-radius:4px;min-width:28px;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0;}
QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal {background:transparent;}
QSlider::groove:horizontal {height:4px;background:#2c3d55;border-radius:2px;}
QSlider::sub-page:horizontal {background:#76e6cd;border-radius:2px;}
QSlider::handle:horizontal {background:#76e6cd;border:2px solid #0d1523;width:12px;height:12px;margin:-6px 0;border-radius:8px;}
QSlider::handle:horizontal:hover {background:#a4f2e1;}
QProgressBar {border:1px solid #2c3d55;border-radius:4px;background:#101c2d;max-height:8px;}
QProgressBar::chunk {background:#76e6cd;border-radius:3px;}
QSplitter::handle {background:transparent;}
QSplitter::handle:hover {background:#2c3d55;}
QStatusBar {color:#9badc5;padding:4px 16px;}
QToolTip {background:#23364d;color:#e5ebf5;border:1px solid #62809c;padding:8px;}
""".replace("ASSETS", assets)
