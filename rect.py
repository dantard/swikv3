from PyQt5.QtCore import pyqtSignal, QObject, QPointF, QRectF
from PyQt5.QtWidgets import QGraphicsRectItem, QMenu

from utils import Signals


class SwikRect(QGraphicsRectItem):

    def __init__(self, parent=None, **kwargs):

        super(SwikRect, self).__init__()
        self.signals = Signals()
        self.setParentItem(parent)
        self.kwargs = None
        self.serialization = {}

        if (item := kwargs.get("copy", None)) is not None:
            self.copy(item, **kwargs)
        else:
            self.apply_kwargs(**kwargs)

    def apply_kwargs(self, **kwargs):
        self.kwargs = kwargs

    def copy(self, item, **kwargs):
        self.setParentItem(item.parentItem())
        self.setRect(item.rect())
        self.setPos(item.pos() + kwargs.get("offset", QPointF(0, 0)))
        self.kwargs = item.get_kwargs()

    def get_rect_on_scene(self):
        return self.sceneBoundingRect()

    def get_rect_on_parent(self):
        if self.parentItem() is None:
            return self.sceneBoundingRect()
        else:
            return self.parentItem().mapRectFromItem(self, self.rect())

    def get_kwargs(self):
        self.kwargs.pop("parent", None)
        return self.kwargs

    def get_kwarg(self, key, default=None):
        return self.kwargs.get(key, default)

    def die(self):
        self.scene().removeItem(self)

    def get_parent(self):
        return self.parentItem()

    def serialize(self, info):
        info["pose"] = self.pos()
        info["rect"] = self.rect()
        info["parent"] = self.get_parent()

    def deserialize(self, info):
        self.setPos(info["pose"])
        self.setRect(info["rect"])
        self.setParentItem(info["parent"])

    def to_yaml(self, info):
        info["pose"] = {"x", self.pos().x(), "y", self.pos().y()}
        info["rect"] = {"x", self.rect().x(), "y", self.rect().y(), "w", self.rect().width(), "h", self.rect().height()}
        info["parent"] = self.parentItem().index if self.parentItem() is not None else None

    def from_yaml(self, info):
        self.setPos(QPointF(info["pose"]["x"], info["pose"]["y"]))
        self.setRect(QRectF(info["rect"]["x"], info["rect"]["y"], info["rect"]["w"], info["rect"]["h"]))

    def get_serialization(self):
        info = {}
        self.serialize(info)
        return info
