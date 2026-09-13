"""Localized application dialogs; native file pickers retain OS conventions."""

from PySide6.QtWidgets import QFileDialog, QMessageBox


class Dialogs:
    @staticmethod
    def message(owner, title, text, icon, buttons):
        box = QMessageBox(icon, owner.t(title), owner.t(text), buttons, owner)
        for value, source in (
            (QMessageBox.Save, "Save"),
            (QMessageBox.Discard, "Discard"),
            (QMessageBox.Cancel, "Cancel"),
            (QMessageBox.Yes, "Yes"),
            (QMessageBox.No, "No"),
            (QMessageBox.Ok, "OK"),
        ):
            button = box.button(value)
            if button:
                button.setText(owner.t(source))
        return box.exec()

    @staticmethod
    def warning(owner, title, text):
        return Dialogs.message(owner, title, text, QMessageBox.Warning, QMessageBox.Ok)

    @staticmethod
    def information(owner, title, text):
        return Dialogs.message(owner, title, text, QMessageBox.Information, QMessageBox.Ok)

    @staticmethod
    def question(owner, title, text, buttons=QMessageBox.Yes | QMessageBox.No):
        return Dialogs.message(owner, title, text, QMessageBox.Question, buttons)

    @staticmethod
    def getOpenFileName(owner, title, directory, filters):
        return QFileDialog.getOpenFileName(owner, owner.t(title), directory, owner.t(filters))

    @staticmethod
    def getSaveFileName(owner, title, filename, filters):
        return QFileDialog.getSaveFileName(owner, owner.t(title), owner.t(filename), owner.t(filters))
