from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import QMenu, QDialog, QGraphicsRectItem

from colorwidget import ColorAlphaWidth, ColorAndAlpha
from dialogs import ComposableDialog
from rect import SwikRect


class ColoreableRectItem(SwikRect):
    def __init__(self, parent=None, **kwargs):
        super(ColoreableRectItem, self).__init__(parent, **kwargs)

    def apply_kwargs(self, **kwargs):
        super().apply_kwargs(**kwargs)
        print("apply colore")
        self.setPen(kwargs.get("pen", QPen(Qt.black)))
        self.setBrush(kwargs.get("brush", QBrush(Qt.transparent)))

    def copy(self, item, **kwargs):
        super().copy(item, **kwargs)
        self.setPen(item.pen())
        self.setBrush(item.brush())

    def set_border_color(self, color: QColor, alpha=255):
        color = QColor(color)
        pen = self.pen()
        pen.setColor(QColor(color.red(), color.green(), color.blue(), alpha))
        self.setPen(pen)

    def set_fill_color(self, color: QColor, alpha=255):
        color = QColor(color)
        brush = QBrush(QColor(color.red(), color.green(), color.blue(), alpha))
        self.setBrush(brush)

    def set_border_width(self, width: int):
        pen = self.pen()
        pen.setWidth(width)
        self.setPen(pen)

    def populate_menu(self, menu: QMenu):
        super().populate_menu(menu)
        menu.addAction("Change color", self.change_color)

    def change_color(self):
        self.serialization = self.get_serialization()

        color = ComposableDialog()
        color.add_row("Border", ColorAlphaWidth(self.pen().color()))
        color.add_row("Fill", ColorAndAlpha(self.brush().color()))

        if color.exec() == QDialog.Accepted:
            self.set_border_color(color.get("Border").get_color())
            self.set_fill_color(color.get("Fill").get_color())

            if self.serialization != self.get_serialization():
                print("changed")
                self.signals.changed.emit(self)

    def serialize(self, info):
        super().serialize(info)
        info["pen"] = self.pen()
        info["brush"] = self.brush()

    def deserialize(self, info):
        super().deserialize(info)
        self.setPen(info["pen"])
        self.setBrush(info["brush"])

    def from_yaml(self, info):
        super().from_yaml(info)
        self.setPen(QPen(QColor(info["pen"]["r"], info["pen"]["g"], info["pen"]["b"], info["pen"]["a"]), info["pen"]["w"]))
        self.setBrush(QBrush(QColor(info["brush"]["r"], info["brush"]["g"], info["brush"]["b"], info["brush"]["a"])))

    def to_yaml(self, info):
        super().to_yaml(info)
        info["pen"] = {"r": self.pen().color().red(), "g": self.pen().color().green(), "b": self.pen().color().blue(), "a": self.pen().color().alpha(), "w": self.pen().width()}
        info["brush"] = {"r": self.brush().color().red(), "g": self.brush().color().green(), "b": self.brush().color().blue(), "a": self.brush().color().alpha()}