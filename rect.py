from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QGraphicsRectItem


class SwikRect(QGraphicsRectItem):

    def __init__(self, parent=None, **kwargs):
        super(SwikRect, self).__init__(parent)
        self.kwargs = kwargs
        if kwargs.get("copy", None) is not None:
            self.copy(kwargs.get("copy"))

    def get_rect_on_scene(self):
        return self.sceneBoundingRect()

    def get_rect_on_parent(self):
        if self.parentItem() is None:
            return self.sceneBoundingRect()
        else:
            return self.parentItem().mapRectFromItem(self, self.rect())

    def copy(self, copy):
        self.setParentItem(copy.parentItem())
        self.setRect(copy.rect())
        self.setPos(copy.pos())
        self.setPen(copy.pen())
        self.setBrush(copy.brush())

    def get_kwargs(self):
        self.kwargs.pop("parent", None)
        return self.kwargs

    def die(self):
        self.scene().removeItem(self)

    def get_parent(self):
        return self.parentItem()
