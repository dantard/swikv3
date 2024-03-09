from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QMenu

from action import Action
from annotations.annotation import Annotation
from colorwidget import Color
from dialogs import ComposableDialog
from resizeable import ResizableRectItem


class RedactAnnotation(ResizableRectItem):

    def change_color(self):
        before = self.brush().color()

        color = ComposableDialog()
        color.add_row("Fill", Color(self.brush().color()))

        if color.exec() == QDialog.Accepted:
            self.set_fill_color(color.get("Fill").get_color())

            if before != self.brush().color():
                self.notify_change(Action.ACTION_COLOR_CHANGED, before, self.brush().color())

    def undo(self, kind, info):
        super().undo(kind, info)
        if kind == Action.ACTION_COLOR_CHANGED:
            self.set_fill_color(info)

    def redo(self, kind, info):
        super().redo(kind, info)
        if kind == Action.ACTION_COLOR_CHANGED:
            self.set_fill_color(info)

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        self.change_color()
