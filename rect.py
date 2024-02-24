from PyQt5.QtWidgets import QGraphicsRectItem


class SwikRect(QGraphicsRectItem):
    def __init__(self, limits=None, **kwargs):
        super(SwikRect, self).__init__()
        self.kwargs = kwargs
        self.limits = limits
        if kwargs.get("copy", None) is not None:
            self.copy(kwargs.get("copy"))

    def get_rect_on_scene(self):
        if self.parentItem() is None:
            return self.sceneBoundingRect()
        return self.mapToScene(self.rect()).boundingRect()

    def get_rect_on_parent(self):
        if self.parentItem() is None:
            return self.sceneBoundingRect()
        else:
            return self.parentItem().mapRectFromItem(self, self.rect())

    def get_rect_on(self, item):
        if self.parentItem() is None:
            return item.mapFromScene(self.sceneBoundingRect()).boundingRect()
        else:
            assert 0
            # return self.mapToItem(item, self.rect()).boundingRect()

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
