from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import QMenu, QDialog, QGraphicsRectItem

from colorwidget import ColorAlphaWidth, ColorAndAlpha
from dialogs import ComposableDialog
from rect import SwikRect


class ColoreableRectItem(SwikRect):
    def __init__(self, parent=None, **kwargs):
        super(ColoreableRectItem, self).__init__(parent, **kwargs)
        if (copy:=kwargs.get("copy", None)) is None:
            self.setPen(kwargs.get("pen", QPen(Qt.black)))
            self.setBrush(kwargs.get("brush", QBrush(Qt.transparent)))
        else:
            #self.setPen(kwargs.get("pen", copy.get_kwargs("pen", QPen(Qt.black))))
            #self.setBrush(kwargs.get("brush", copy.get_kwargs("brush",QBrush(Qt.transparent)))
            pass

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
        color = ComposableDialog()
        color.add_row("Border", ColorAlphaWidth(self.pen().color()))
        color.add_row("Fill", ColorAndAlpha(self.brush().color()))

        if color.exec() == QDialog.Accepted:
            self.set_border_color(color.get("Border").get_color())
            self.set_fill_color(color.get("Fill").get_color())
