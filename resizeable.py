import random
import sys

import typing
from PyQt5 import QtGui
from PyQt5.QtGui import QImage, QFont, QFontMetrics, QColor, QBrush, QPen
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QWidget, QStyle, QMenu, QDialog, QSlider
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, QObject, pyqtSignal

from coloreable import ColoreableRectItem
from colorwidget import ColorWidget, ColorAndAlpha, ColorAlphaWidth
from dialogs import ComposableDialog
from paintable import PaintableRectItem
from selector import SelectorRectItem, PaintableSelectorRectItem
from utils import Signals, check_parent_limits


class HandleItem(QGraphicsRectItem):
    def __init__(self, parent):
        super().__init__(-5, -5, 10, 10, parent=parent)
        self.setBrush(Qt.white)
        self.setPen(Qt.black)
        self.setFlags(QGraphicsRectItem.ItemIsMovable | QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        self.setBrush(Qt.black)
        super().hoverEnterEvent(event)
        self.parentItem().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(Qt.white)
        super().hoverLeaveEvent(event)
        self.parentItem().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        super(HandleItem, self).mousePressEvent(event)
        self.parentItem().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super(HandleItem, self).mouseMoveEvent(event)
        self.parentItem().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super(HandleItem, self).mouseReleaseEvent(event)
        self.parentItem().mouseReleaseEvent(event)

    def paint(self, painter: QtGui.QPainter, option, widget: typing.Optional[QWidget] = ...) -> None:
        option.state = QStyle.State_None
        super().paint(painter, option, widget)


class SelectorPaintableRectItem(SelectorRectItem, PaintableRectItem):
    pass


class ResizableRectItem(PaintableSelectorRectItem):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        # super(ColoreableRectItem, self).__init__(parent, **kwargs)

        self.signals = Signals()
        self.resizeable = True
        self.movable = True
        self.setFlags(QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.handle_size = 10  # Size of resize handles
        self.handle_pressed = None
        self.handles_enabled = True
        self.handles = []

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.set_handle_visibility(False))
        self.timer.setInterval(2000)

        for i in range(8):
            handle = HandleItem(self)
            handle.setBrush(Qt.white)
            handle.setPen(Qt.black)
            handle.setFlag(QGraphicsRectItem.ItemIsMovable, False)
            handle.setAcceptHoverEvents(True)
            handle.setVisible(False)
            self.handles.append(handle)

        self.update_handles_position()

    def set_movable(self, movable):
        self.movable = movable

    def set_resizeable(self, resizeable):
        self.resizeable = resizeable

    def get_resizeable(self):
        return self.resizeable

    def get_movable(self):
        return self.movable

    def set_handles_enabled(self, enabled):
        self.handles_enabled = enabled

    def get_handles_enabled(self):
        return self.handles_enabled

    def update_handles_position(self):
        bounds = self.rect()
        handle_positions = [
            QPointF(bounds.left(), bounds.top()),
            QPointF(bounds.center().x(), bounds.top()),
            QPointF(bounds.right(), bounds.top()),
            QPointF(bounds.right(), bounds.center().y()),
            QPointF(bounds.right(), bounds.bottom()),
            QPointF(bounds.center().x(), bounds.bottom()),
            QPointF(bounds.left(), bounds.bottom()),
            QPointF(bounds.left(), bounds.center().y()),
        ]

        for handle, pos in zip(self.handles, handle_positions):
            handle.setPos(pos)

    def hoverMoveEvent(self, event):
        self.set_handle_visibility(True)
        self.timer.stop()
        if not self.handle_pressed:
            self.timer.start()

        if any(handle.contains(handle.mapFromScene(event.scenePos())) for handle in self.handles):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        for handle in self.handles:
            if handle.contains(handle.mapFromScene(event.scenePos())):
                self.handle_pressed: HandleItem = handle
                self.prev_pos = self.mapFromScene(handle.sceneBoundingRect().center())  # event.scenePos()
                break
        else:
            super().mousePressEvent(event)
            self.point = self.mapFromScene(event.scenePos())

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.set_handle_visibility(True)
        self.timer.stop()

        if self.handle_pressed:
            x, y = event.scenePos().x(), event.scenePos().y()
            if self.limits is not None:
                x, y = check_parent_limits(self.limits, x, y)

            new_pos = self.mapFromScene(x, y)

            delta = new_pos - self.prev_pos
            rect = self.rect()

            if self.handle_pressed == self.handles[0]:
                rect.setTopLeft(rect.topLeft() + delta)
            elif self.handle_pressed == self.handles[1]:
                rect.setTop(rect.top() + delta.y())
            elif self.handle_pressed == self.handles[2]:
                rect.setTopRight(rect.topRight() + delta)
            elif self.handle_pressed == self.handles[3]:
                rect.setRight(rect.right() + delta.x())
            elif self.handle_pressed == self.handles[4]:
                rect.setBottomRight(rect.bottomRight() + delta)
            elif self.handle_pressed == self.handles[5]:
                rect.setBottom(rect.bottom() + delta.y())
            elif self.handle_pressed == self.handles[6]:
                rect.setBottomLeft(rect.bottomLeft() + delta)
            elif self.handle_pressed == self.handles[7]:
                rect.setLeft(rect.left() + delta.x())

            if self.limits is not None:
                rect = self.mapRectToScene(rect)
                x1, y1, x2, y2 = rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()

                x1, y1 = check_parent_limits(self.limits, x1, y1)
                x2, y2 = check_parent_limits(self.limits, x2, y2)

                rect = self.mapFromScene(QRectF(x1, y1, x2 - x1, y2 - y1).normalized()).boundingRect()

            self.setRect(rect.normalized())
            self.update_handles_position()
            self.prev_pos = new_pos
            self.signals.resizing.emit(self)

        else:
            scene_pos = event.scenePos() - self.point
            if self.limits is not None:

                x1, y1 = (scene_pos + self.rect().topLeft()).x(), (scene_pos + self.rect().topLeft()).y()
                x1, y1 = check_parent_limits(self.limits, x1, y1)

                x2, y2 = x1 + self.rect().bottomRight().x(), y1 + self.rect().bottomRight().y()
                x2, y2 = check_parent_limits(self.limits, x2, y2)
                x, y = x2 - self.rect().width(), y2 - self.rect().height()

                pos = QPointF(x, y)
            else:
                pos = scene_pos

            if self.movable:
                self.signals.moving.emit(self)
                print('moving', self, pos)
                self.setPos(pos)
                self.update()

            self.timer.start()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setPos(self.pos().x() + self.rect().x(), self.pos().y() + self.rect().y())
        self.setRect(0, 0, self.rect().width(), self.rect().height())
        self.update_handles_position()
        self.handle_pressed = None
        self.timer.start()

    def view_mouse_release_event(self, view, event):
        super(ResizableRectItem, self).view_mouse_release_event(view, event)
        self.update_handles_position()

    def set_handle_visibility(self, visible: bool):
        for handle in self.handles:
            handle.setVisible(visible and self.handles_enabled)

    def hoverEnterEvent(self, event) -> None:
        self.set_handle_visibility(True)

    # Only if derived from Paintableselector
    # def view_mouse_release_event(self, view, event):
    #    super().view_mouse_release_event(view, event)
    #    self.update_handles_position()
    #    self.handles_enabled = True

    def populate_menu(self, menu: QMenu):
        menu.addAction("Delete", lambda: self.scene().removeItem(self))

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        menu = QMenu()
        self.populate_menu(menu)
        menu.exec(event.screenPos())


class MainWindow(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.rect_item = None
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.padre = self.scene.addRect(0, 0, 400, 400, pen=Qt.red)
        self.padre.setPos(50, 50)
        self.scene.addRect(0, 0, 800, 800, pen=Qt.red)
        self.done = 0

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:

        if self.done < 1:
            # self.rect_item = PaintableSelectorRectItem(text="hola")
            self.rect_item = ResizableRectItem(self.padre, text="hola")
            # self.rect_item = FancyResizableRectItem(pen=Qt.red, brush=Qt.green)
            # self.rect_item.set_border_width(5)
            # self.rect_item.set_fill_color(Qt.red, 111)

            # self.rect_item.set_movable(False)
            self.scene.addItem(self.rect_item)
            self.rect_item.view_mouse_press_event(self, event)
            self.rect_item.signals.done.connect(self.draw_done)
            self.rect_item.signals.moving.connect(lambda x: print("moving"))
            self.rect_item.signals.resizing.connect(lambda x: print("resizing"))
            # self.rect_item.signals.creating.connect(lambda x: print("creating"))

        super().mousePressEvent(event)

    def draw_done(self):
        return
        for w, k in self.rect_item.get_kwargs().items():
            print(w, k)
        tmp = self.rect_item
        new = ResizableRectItem(**self.rect_item.get_kwargs(), copy=self.rect_item)

        new.setPos(tmp.pos())
        new.setRect(tmp.rect())
        self.scene.removeItem(self.rect_item)
        self.scene.addItem(new)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self.rect_item is not None:
            self.rect_item.view_mouse_move_event(self, event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if self.rect_item is not None:
            self.rect_item.view_mouse_release_event(self, event)
        self.done = self.done + 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
