from PyQt5.QtCore import QRectF, Qt, QPointF
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem


class HighlightAnnotation(QGraphicsRectItem):
    class Quad(QGraphicsRectItem):

        def __init__(self, parent):
            super().__init__()
            self.setParentItem(parent)

        def mouseDoubleClickEvent(self, event) -> None:
            super().mouseDoubleClickEvent(event)
            self.parentItem().quad_double_click(event)

    def __init__(self, color, parent):
        super().__init__()
        self.quads = []
        self.setParentItem(parent)
        self.color = color
        self.setBrush(Qt.transparent)
        self.setPen(Qt.transparent)

    def get_color(self):
        return self.color

    def quad_double_click(self, event):
        print("quad double click")

    def add_quad(self, rect):
        quad = self.Quad(self)
        quad.setBrush(self.color)
        quad.setPen(Qt.transparent)
        x, y = rect.x(), rect.y()
        w, h = rect.width(), rect.height()
        quad.setZValue(1)

        quad.setRect(QRectF(0, 0, w, h))
        pos = self.mapFromParent(QPointF(x, y))
        quad.setPos(pos)
        self.quads.append(quad)

    def get_quads(self):
        quads_on_page = []
        for quad in self.quads:
            quad_on_annotation = QRectF(quad.pos().x(), quad.pos().y(), quad.rect().width(), quad.rect().height())
            quad_on_page = self.mapRectToParent(quad_on_annotation)
            quads_on_page.append(quad_on_page)
            print(quad_on_page)
        return quads_on_page
