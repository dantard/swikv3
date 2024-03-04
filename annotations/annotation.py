from PyQt5.QtWidgets import QDialog, QMenu

from action import Action
from colorwidget import ColorAlphaAndWidth, ColorAndAlpha, TextLineEdit
from dialogs import ComposableDialog
from resizeable import ResizableRectItem


class Annotation(ResizableRectItem):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.content = str()

    def set_content(self, text):
        self.content = text

    def get_content(self):
        return self.content

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        self.change_color()

    def change_color(self):
        before = [self.brush().color(), self.pen().color(), self.pen().width(), self.content]

        color = ComposableDialog()
        color.add_row("Content", TextLineEdit(self.content))
        color.add_row("Border", ColorAlphaAndWidth(self.pen()))
        color.add_row("Fill", ColorAndAlpha(self.brush().color()))

        if color.exec() == QDialog.Accepted:
            self.set_border_color(color.get("Border").get_color())
            self.set_border_width(color.get("Border").get_width())
            c1 = color.get("Fill").get_color()
            print("C1", c1.red(), c1.green(), c1.blue(), c1.alpha())
            self.set_fill_color(color.get("Fill").get_color())
            self.set_content(color.get("Content").get_text())
            self.setToolTip(self.get_content())

        after = [self.brush().color(), self.pen().color(), self.pen().width(), self.content]

        if after != before:
            self.notify_change(Action.ACTION_ANNOT_CHANGED, before, after)

    def undo(self, kind, info):
        super().undo(kind, info)
        if kind == Action.ACTION_ANNOT_CHANGED:
            self.set_fill_color(info[0])
            self.set_border_color(info[1])
            self.set_border_width(info[2])
            self.set_content(info[3])

    def redo(self, kind, info):
        super().redo(kind, info)
        if kind == Action.ACTION_ANNOT_CHANGED:
            self.set_fill_color(info[0])
            self.set_border_color(info[1])
            self.set_border_width(info[2])
            self.set_content(info[3])


# Compare this snippet from annotations/annotation.py:
