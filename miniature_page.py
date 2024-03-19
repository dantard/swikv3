import typing

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPointF, QObject, QPoint, QThread
from PyQt5.QtGui import QBrush, QColor, QFontMetrics, QTransform, QPen
from PyQt5.QtWidgets import QWidget, QGraphicsPixmapItem, \
    QGraphicsView, QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem, QMenu

from simplepage import SimplePage


class MiniaturePage(SimplePage):
    def __init__(self, index, view, manager, renderer, ratio):
        super().__init__(index, view, manager, renderer, ratio)
        self.background = None

    def get_sep(self):
        self.number.setPlainText(str(self.index + 1))
        return 60  # + 30 * self.get_scaling_ratio()

    def update_image(self, ratio):
        super().update_image(ratio)
        if self.background is not None:
            self.background.setPos(0, self.rect().height() + 10 / self.ratio)
            self.background.setRect(QRectF(0, 0, self.boundingRect().width() * self.ratio, 35))
            center = (self.background.rect().width() - self.number.boundingRect().width()) / 2
            self.number.setPos(center, 0)

    def connect_signals(self):
        super().connect_signals()

        self.background = QGraphicsRectItem(self)
        self.background.setBrush(QBrush(QColor(180, 180, 180, 255)))
        # self.background.setPen(QColor(180,180,180,255))
        self.background.setRect(QRectF(0, 0, self.boundingRect().width(), 55))
        self.background.setPos(0, self.boundingRect().height() + 10)
        self.background.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        self.number = QGraphicsTextItem(self.background)
        font = self.number.font()
        self.number.setPlainText(str(self.index + 1))  # + "." + str(self.renderer.document[self.index].rotation))
        font.setPixelSize(22)
        self.number.setFont(font)
        center = (self.rect().width() - self.number.boundingRect().width() * 2) / 2
        self.number.setPos(center, self.boundingRect().height() + 10)
        self.number.setFlag(QGraphicsItem.ItemIgnoresTransformations)

    def set_highlighted(self, value):
        if value:
            self.box.setBrush(QBrush(QColor(255, 0, 0, 30)))
            self.background.setBrush(QBrush(QColor(255, 180, 180, 255)))
        else:
            self.background.setBrush(QBrush(QColor(180, 180, 180, 255)))

        self.box.setVisible(value)
