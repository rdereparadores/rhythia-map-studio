"""Translate UI presentation while retaining canonical combo values and state."""

from PySide6.QtCore import QLocale, QSignalBlocker
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QWidget,
)


class UiTranslations:
    def __init__(self, window):
        self.bindings = []
        for widget in window.findChildren(QWidget):
            if widget.toolTip():
                self.bindings.append((widget, widget.setToolTip, widget.toolTip()))
            if isinstance(widget, (QLabel, QAbstractButton)) and not widget.property("dynamicText"):
                self.bindings.append((widget, widget.setText, widget.text()))
            if isinstance(widget, QLineEdit) and not isinstance(widget.parent(), QAbstractSpinBox):
                self.bindings.append((widget, widget.setPlaceholderText, widget.placeholderText()))
            if isinstance(widget, QComboBox) and widget is not window.view.language:
                for index in range(widget.count()):
                    source = widget.itemText(index)
                    self.bindings.append(
                        (widget, lambda text, w=widget, i=index: w.setItemText(i, text), source)
                    )
            if isinstance(widget, QTabWidget):
                for index in range(widget.count()):
                    self.bindings.append(
                        (widget, lambda text, w=widget, i=index: w.setTabText(i, text), widget.tabText(index))
                    )
            if isinstance(widget, QTableWidget):
                for index in range(widget.columnCount()):
                    item = widget.horizontalHeaderItem(index)
                    self.bindings.append((widget, item.setText, item.text()))
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                self.bindings.append((widget, widget.setSpecialValueText, widget.specialValueText()))

    def apply(self, window):
        window.setLocale(QLocale(window.translator.locale))
        for widget, setter, source in self.bindings:
            blocker = QSignalBlocker(widget)
            setter(window.t(source))
            del blocker
