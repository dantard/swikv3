import random
import sys

import typing
from PyQt5 import QtGui
from PyQt5.QtGui import QImage, QFont, QFontMetrics
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QWidget, QStyle
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer


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


class ResizableRectItem(QGraphicsRectItem):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFlags(QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.handle_size = 10  # Size of resize handles
        self.handle_pressed = None
        self.handles_enabled = False
        self.handles = []
        self.p1 = None

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
            self.begin = self.mapFromScene(event.scenePos())

    def mouseMoveEvent(self, event):
        self.set_handle_visibility(True)
        self.timer.stop()
        super().mouseMoveEvent(event)

        if self.handle_pressed:
            x, y = event.scenePos().x(), event.scenePos().y()
            if self.parentItem() is not None:
                x, y = self.check_parent_limits(self.parentItem(), x, y)

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

            if self.parentItem() is not None:
                rect = self.mapRectToScene(rect)
                x1, y1, x2, y2 = rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()

                x1, y1 = self.check_parent_limits(self.parentItem(), x1, y1)
                x2, y2 = self.check_parent_limits(self.parentItem(), x2, y2)

                rect = self.mapFromScene(QRectF(x1, y1, x2 - x1, y2 - y1).normalized()).boundingRect()

            self.setRect(rect.normalized())
            self.update_handles_position()
            self.prev_pos = new_pos

        else:
            scene_pos = event.scenePos() - self.begin
            if self.parentItem() is not None:

                x1, y1 = (scene_pos + self.rect().topLeft()).x(), (scene_pos + self.rect().topLeft()).y()
                x1, y1 = self.check_parent_limits(self.parentItem(), x1, y1)

                x2, y2 = x1 + self.rect().bottomRight().x(), y1 + self.rect().bottomRight().y()
                x2, y2 = self.check_parent_limits(self.parentItem(), x2, y2)
                x, y = x2 - self.rect().width(), y2 - self.rect().height()

                on_parent = self.parentItem().mapFromScene(x, y)
                self.setPos(on_parent)
            else:
                self.setPos(scene_pos)
                self.timer.start()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.handle_pressed = None
        self.timer.start()
        self.setPos(self.pos().x() + self.rect().x(), self.pos().y() + self.rect().y())
        self.setRect(0, 0, self.rect().width(), self.rect().height())

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionHasChanged:
            self.update_handles_position()
        return super().itemChange(change, value)

    def set_handle_visibility(self, visible: bool):
        for handle in self.handles:
            handle.setVisible(visible and self.handles_enabled)

    def hoverEnterEvent(self, event) -> None:
        self.set_handle_visibility(True)

    def view_mouse_press_event(self, view, event):
        if self.parentItem() is None:
            self.p1 = view.mapToScene(event.pos())
        else:
            self.p1 = self.parentItem().mapFromScene(view.mapToScene(event.pos()))

        self.setPos(self.p1)
        self.setRect(QRectF(0, 0, 0, 0))

    def check_parent_limits(self, parent: QGraphicsRectItem, scene_x, scene_y):
        if parent is not None:
            pos_on_item = parent.mapFromScene(scene_x, scene_y)
            x, y = pos_on_item.x(), pos_on_item.y()
            x = parent.rect().x() if x < parent.rect().x() else x
            x = parent.rect().x() + parent.rect().width() if x > parent.rect().x() + parent.rect().width() else x
            y = parent.rect().y() if y < parent.rect().y() else y
            y = parent.rect().y() + parent.rect().height() if y > parent.rect().y() + parent.rect().height() else y
            point_on_scene = parent.mapToScene(x, y)
            x, y = point_on_scene.x(), point_on_scene.y()
        else:
            x, y = scene_x, scene_y

        return x, y

    def view_mouse_move_event(self, view, event):
        if self.p1 is not None:
            scene_x, scene_y = view.mapToScene(event.pos()).x(), view.mapToScene(event.pos()).y()
            x, y = self.check_parent_limits(self.parentItem(), scene_x, scene_y)
            if self.parentItem() is not None:
                pose_on_parent = self.parentItem().mapFromScene(x, y)
                x, y = pose_on_parent.x(), pose_on_parent.y()

            self.setRect(QRectF(0, 0, x - self.p1.x(), y - self.p1.y()).normalized())

    def view_mouse_release_event(self, view, event):
        self.update_handles_position()
        self.handles_enabled = True
        self.p1 = None


class FancyResizableRectItem(ResizableRectItem):
    TEXT_MODE_STRETCH = 0
    TEXT_MODE_KEEP = 1
    IMAGE_MODE_STRETCH = 3
    IMAGE_MODE_MAINTAIN_RATIO = 1
    IMAGE_MODE_DONT_MAINTAIN_RATIO =0
    IMAGE_MODE_MAINTAIN_SIZE = 2

    def __init__(self):
        super(FancyResizableRectItem, self).__init__()
        self.image_mode = 4
        self.image = QImage("/home/danilo/Pictures/kakka.png")
        self.text = "Hola"
        self.text_mode = self.TEXT_MODE_KEEP
        self.max_font_size = 55
        self.font = QFont("Helvetica")

    def paint(self, painter: QtGui.QPainter, option, widget: typing.Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)

        # if self.init_pos is None:
        #    return

        if self.image is not None:
            if self.image_mode == 1:
                rw, rh = self.rect().width(), self.rect().height()
                iw, ih = self.image.width(), self.image.height()
                if rw != 0 and iw != 0 and ih != 0:
                    i_ratio = ih / iw
                    r_ratio = rh / rw
                    if r_ratio > i_ratio:
                        ratio = rw / iw
                    else:
                        ratio = rh / ih

                    qr = QRectF(self.rect().x(), self.rect().y(), iw * ratio, ih * ratio)
                    painter.drawImage(qr, self.image)
            elif self.image_mode == 2:
                painter.drawImage(QPointF(self.rect().x(), self.rect().y()), self.image, QRectF(0, 0, self.rect().width(), self.rect().height()))
            elif self.image_mode == 3:
                painter.drawImage(self.rect(), self.image)
            elif self.image_mode == 4:
                painter.drawImage(QRectF(0, 0, self.image.width(), self.image.height()), self.image)

        if self.text is not None:
            font_size = self.max_font_size  # * self.init_pos_item.get_scaling_ratio()
            if self.text_mode == self.TEXT_MODE_STRETCH:
                while True:
                    self.font.setPixelSize(max(int(font_size), 1))
                    fm = QFontMetrics(self.font)
                    maxi, lines = 0, self.text.split("\n")
                    for line in lines:
                        maxi = max(fm.horizontalAdvance(line), maxi)

                    font_size = font_size - 1
                    if (maxi <= self.rect().width() and len(lines) * fm.height() <= self.rect().height() + 4) or font_size <= 1:
                        break
            else:
                self.font.setPixelSize(int(max(font_size, 1)))

            painter.setFont(self.font)
            painter.setPen(Qt.black)
            painter.drawText(self.rect(), 0, self.text)

class MainWindow(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.rect_item = None
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.padre = self.scene.addRect(0, 0, 400, 400, pen=Qt.red)
        self.padre.setPos(50, 50)
        self.scene.addRect(0, 0, 800, 800, pen=Qt.red)
        self.done = False

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:

        if not self.done:
            self.rect_item = ResizableRectItem(self.padre)
            self.rect_item = FancyResizableRectItem()
            self.scene.addItem(self.rect_item)
            self.rect_item.view_mouse_press_event(self, event)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self.rect_item is not None:
            self.rect_item.view_mouse_move_event(self, event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if self.rect_item is not None:
            self.rect_item.view_mouse_release_event(self, event)
        self.done = True




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
