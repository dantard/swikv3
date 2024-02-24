from PyQt5.QtCore import QObject, QRectF
from PyQt5.QtWidgets import QGraphicsRectItem

from coloreable import ColoreableRectItem
from paintable import PaintableRectItem
from utils import Signals, check_parent_limits


class SelectorRectItem(ColoreableRectItem):
    def __init__(self, limits=None, **kwargs):
        super().__init__(limits, **kwargs)
        self.signals = Signals()
        self.p1 = None
        self.p2 = None

    def get_click_pos(self):
        return self.p1

    def view_mouse_press_event(self, view, event):

        self.p1 = view.mapToScene(event.pos())

        self.setPos(self.p1)
        self.setRect(QRectF(0, 0, 0, 0))

    def view_mouse_move_event(self, view, event):
        if self.p1 is not None:
            scene_x, scene_y = view.mapToScene(event.pos()).x(), view.mapToScene(event.pos()).y()
            x, y = check_parent_limits(self.limits, scene_x, scene_y)

            self.setRect(QRectF(0, 0, x - self.p1.x(), y - self.p1.y()).normalized())
            self.p2 = view.mapToScene(event.pos())
            self.signals.creating.emit(self)

    def get_mouse_pos(self):
        return self.p2

    def view_mouse_release_event(self, view, event):
        if self.p1 is not None:
            self.p1 = None
            self.signals.done.emit(self)


class PaintableSelectorRectItem(SelectorRectItem, PaintableRectItem):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        super(ColoreableRectItem, self).__init__(parent, **kwargs)
