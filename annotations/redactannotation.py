from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from action import Action
from annotations.annotation import Annotation
from colorwidget import Color
from dialogs import ComposableDialog
from resizeable import ResizableRectItem


class RedactAnnotation(ResizableRectItem):
    def change_color(self):
        self.serialization = self.get_serialization()

        color = ComposableDialog()
        color.add_row("Fill", Color(self.brush().color()))

        if color.exec() == QDialog.Accepted:
            self.set_fill_color(color.get("Fill").get_color())

        if self.serialization != self.get_serialization():
            print("color changed")
        self.notify_change(Action.ACTION_FULL_STATE, self.serialization, self.get_serialization())


