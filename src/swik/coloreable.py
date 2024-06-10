from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor

from swik.rect import SwikRect


class ColoreableRectItem(SwikRect):
    def __init__(self, parent=None, **kwargs):
        super(ColoreableRectItem, self).__init__(parent, **kwargs)
        #super(Undoable, self).__init__()

    def apply_kwargs(self, **kwargs):
        super().apply_kwargs(**kwargs)
        self.setPen(kwargs.get("pen", QPen(Qt.black)))
        self.setBrush(kwargs.get("brush", QBrush(Qt.transparent)))

    def copy(self, item, **kwargs):
        super().copy(item, **kwargs)
        self.setPen(item.pen())
        self.setBrush(item.brush())

    def set_border_color(self, color: QColor):
        color = QColor(color)
        pen = self.pen()
        pen.setColor(color)
        self.setPen(pen)

    def set_fill_color(self, color: QColor):
        color = QColor(color)
        brush = QBrush(color)
        self.setBrush(brush)

    def set_border_width(self, width: int):
        print("set border width", width)
        pen = self.pen()
        pen.setWidth(int(width))
        self.setPen(pen)

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
        info["pen"] = {"r": self.pen().color().red(), "g": self.pen().color().green(), "b": self.pen().color().blue(), "a": self.pen().color().alpha(),
                       "w": self.pen().width()}
        info["brush"] = {"r": self.brush().color().red(), "g": self.brush().color().green(), "b": self.brush().color().blue(),
                         "a": self.brush().color().alpha()}
