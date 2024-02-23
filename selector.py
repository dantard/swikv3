from PyQt5.QtCore import QObject, QRectF
from PyQt5.QtWidgets import QGraphicsRectItem

from coloreable import ColoreableRectItem
from paintable import PaintableRectItem
from utils import Signals, check_parent_limits


class SelectorRectItem(ColoreableRectItem):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.signals = Signals()
        self.p1 = None
        self.p2 = None

    def get_click_pos(self):
        return self.p1

    def view_mouse_press_event(self, view, event):
        if self.parentItem() is None:
            self.p1 = view.mapToScene(event.pos())
        else:
            self.p1 = self.parentItem().mapFromScene(view.mapToScene(event.pos()))

        self.setPos(self.p1)
        self.setRect(QRectF(0, 0, 0, 0))

    def view_mouse_move_event(self, view, event):
        if self.p1 is not None:
            scene_x, scene_y = view.mapToScene(event.pos()).x(), view.mapToScene(event.pos()).y()
            x, y = check_parent_limits(self.parentItem(), scene_x, scene_y)
            if self.parentItem() is not None:
                pose_on_parent = self.parentItem().mapFromScene(x, y)
                x, y = pose_on_parent.x(), pose_on_parent.y()

            self.setRect(QRectF(0, 0, x - self.p1.x(), y - self.p1.y()).normalized())

            if self.parentItem() is None:
                self.p2 = view.mapToScene(event.pos())
            else:
                self.p2 = self.parentItem().mapFromScene(view.mapToScene(event.pos()))

            self.signals.creating.emit(self)

    def get_mouse_pos(self):
        return self.p2

    def view_mouse_release_event(self, view, event):
        if self.p1 is not None:
            self.signals.done.emit(self)
        self.p1 = None


class PaintableSelectorRectItem(SelectorRectItem, PaintableRectItem):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        super(ColoreableRectItem, self).__init__(parent, **kwargs)
