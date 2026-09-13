"""Painted playback grid and zoomable beat/section timeline."""

import bisect

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

COLORS = ("#76e6cd", "#ad9af5", "#ffcc7d", "#79bafa", "#f28fa6", "#b4d578")


def group_color(group):
    return QColor(COLORS[sum(ord(c) for c in group) % len(COLORS)])


class Grid(QWidget):
    moved = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(280, 250)
        self.notes = []
        self.time = 0
        self.selected = -1

    def bounds(self):
        side = min(self.width() - 65, self.height() - 65)
        return (self.width() - side) / 2, (self.height() - side) / 2, side / 3

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        x, y, cell = self.bounds()
        p.setPen(QPen(QColor("#2d3b53"), 1))
        p.setBrush(QColor("#111d30"))
        p.drawRoundedRect(QRectF(x, y, cell * 3, cell * 3), 12, 12)
        for r in range(3):
            for c in range(3):
                p.drawText(QRectF(x + c * cell, y + r * cell, cell, cell), Qt.AlignCenter, "·")
        times = [n["Time"] for n in self.notes]
        begin = bisect.bisect_left(times, self.time - 70)
        end = bisect.bisect_right(times, self.time + 950)
        for i in reversed(range(begin, end)):
            n = self.notes[i]
            remaining = n["Time"] - self.time
            cx, cy = x + (n["X"] + 0.5) * cell, y + (n["Y"] + 0.5) * cell
            radius = cell * 0.2
            color = group_color(n.get("Section", "U1"))
            color.setAlphaF(max(0.15, min(1, 1 - remaining / 1300)))
            p.setPen(QPen(color, 2))
            p.setBrush(QColor("#1c3d40"))
            p.drawRoundedRect(QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius), 6, 6)
            p.setBrush(Qt.NoBrush)
            approach = radius * (1 + max(0, remaining) / 600)
            p.drawEllipse(QRectF(cx - approach, cy - approach, approach * 2, approach * 2))
            p.drawText(QRectF(cx - radius, cy - radius, radius * 2, radius * 2), Qt.AlignCenter, str(i + 1))
        if 0 <= self.selected < len(self.notes):
            n = self.notes[self.selected]
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor("#ffcc7d"), 3))
            p.drawRoundedRect(QRectF(x + n["X"] * cell + 4, y + n["Y"] * cell + 4, cell - 8, cell - 8), 8, 8)
        p.end()

    def mouseReleaseEvent(self, event):
        x, y, cell = self.bounds()
        col, row = int((event.position().x() - x) // cell), int((event.position().y() - y) // cell)
        if 0 <= col < 3 and 0 <= row < 3:
            self.moved.emit(col, row)


class Timeline(QWidget):
    seek = Signal(int)
    range_selected = Signal(int, int)
    note_dragged = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(145)
        self.setMaximumHeight(180)
        self.wave = []
        self.notes = []
        self.beats = []
        self.sections = []
        self.duration = 1
        self.time = 0
        self.start = 0
        self.span = 1
        self.selection = (0, 0)
        self.drag_index = None
        self.drag_origin = None
        self.drag_time = None
        self.setToolTip("Wheel: zoom · Shift-drag: select a range · Drag a note marker to move its timing.")

    def set_analysis(self, a):
        self.duration = a["duration_ms"]
        self.wave = a["waveform"]
        self.beats = a.get("beats_ms", [])
        self.sections = a.get("sections", [])
        self.start = 0
        self.span = self.duration
        self.update()

    def x_to_time(self, x):
        return int(max(0, min(self.duration - 1, self.start + x / max(1, self.width()) * self.span)))

    def tx(self, time):
        return (time - self.start) / self.span * self.width()

    def zoom(self, factor, anchor=None):
        anchor = self.time if anchor is None else anchor
        fraction = (anchor - self.start) / max(1, self.span)
        self.span = max(1000, min(self.duration, self.span * factor))
        self.start = max(0, min(self.duration - self.span, anchor - fraction * self.span))
        self.update()

    def show_all(self):
        self.start = 0
        self.span = self.duration
        self.update()

    def set_position(self, time):
        self.time = time
        if not self.start <= time <= self.start + self.span:
            self.start = max(0, min(self.duration - self.span, time - self.span * 0.2))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#0b1422"))
        for section in self.sections:
            a, b = self.tx(section["start_ms"]), self.tx(section["end_ms"])
            if b < 0 or a > self.width():
                continue
            color = group_color(section["group"]) if section["repeated"] else QColor("#31425b")
            p.fillRect(QRectF(a, 0, b - a, 22), color)
            p.setPen(QColor("#0b1724") if section["repeated"] else QColor("#b5c2d4"))
            if b - a > 25:
                p.drawText(
                    QRectF(max(0, a) + 3, 0, min(b, self.width()) - max(0, a) - 3, 22),
                    Qt.AlignVCenter,
                    section["group"],
                )
        for index, beat in enumerate(self.beats):
            x = self.tx(beat)
            if 0 <= x <= self.width() and self.span < 45000:
                p.setPen(QColor("#344c66" if index % 4 == 0 else "#203146"))
                p.drawLine(round(x), 23, round(x), self.height())
        p.setPen(QColor("#4e7886"))
        for i, value in enumerate(self.wave):
            x = self.tx(i / max(1, len(self.wave) - 1) * self.duration)
            if 0 <= x <= self.width():
                h = min(35, value * 45)
                p.drawLine(round(x), round(66 - h), round(x), round(66 + h))
        for n in self.notes:
            x = self.tx(n["Time"])
            if 0 <= x <= self.width():
                p.setPen(
                    QPen(QColor("#ffcc7d") if n.get("Edited") else group_color(n.get("Section", "U1")), 2)
                )
                p.drawLine(round(x), 108, round(x), 122)
        a, b = self.selection
        if b > a:
            p.fillRect(
                QRectF(self.tx(a), 23, self.tx(b) - self.tx(a), self.height() - 23), QColor(130, 180, 240, 40)
            )
        p.setPen(QPen(QColor("#ffcc7d"), 2))
        p.drawLine(round(self.tx(self.time)), 0, round(self.tx(self.time)), self.height())
        if self.drag_time is not None:
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.drawLine(round(self.tx(self.drag_time)), 95, round(self.tx(self.drag_time)), 130)
        p.setPen(QColor("#a0b2c9"))
        p.drawText(6, self.height() - 4, f"{self.start / 1000:.1f} s")
        p.drawText(self.width() - 78, self.height() - 4, f"{(self.start + self.span) / 1000:.1f} s")
        p.end()

    def wheelEvent(self, event):
        self.zoom(0.7 if event.angleDelta().y() > 0 else 1 / 0.7, self.x_to_time(event.position().x()))

    def mousePressEvent(self, event):
        time = self.x_to_time(event.position().x())
        if event.modifiers() & Qt.ShiftModifier:
            self.drag_origin = time
            self.selection = (time, time)
        elif event.position().y() >= 103 and self.notes:
            i = min(
                range(len(self.notes)),
                key=lambda i: abs(self.tx(self.notes[i]["Time"]) - event.position().x()),
            )
            if abs(self.tx(self.notes[i]["Time"]) - event.position().x()) < 8:
                self.drag_index = i
                self.drag_time = self.notes[i]["Time"]
            else:
                self.seek.emit(time)
        else:
            self.seek.emit(time)

    def mouseMoveEvent(self, event):
        time = self.x_to_time(event.position().x())
        if self.drag_origin is not None:
            self.selection = tuple(sorted((self.drag_origin, time)))
        elif self.drag_index is not None:
            self.drag_time = time
        self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_origin is not None:
            self.range_selected.emit(*self.selection)
        elif self.drag_index is not None:
            self.note_dragged.emit(self.drag_index, self.x_to_time(event.position().x()))
        self.drag_origin, self.drag_index, self.drag_time = None, None, None
        self.update()
