import queue
import typing

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPointF, QObject, QPoint, QThread, QMutex, QThreadPool, QRect, QTimer
from PyQt5.QtGui import QBrush, QColor, QFontMetrics, QTransform, QPen, QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QGraphicsPixmapItem, \
    QGraphicsView, QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem, QMenu, QApplication


class SimplePage(QGraphicsRectItem):
    STATE_BLANK = 0
    STATE_WAITING_FINAL = 1
    STATE_FINAL = 2
    STATE_INVALID = 3
    STATE_FORCED = 4
    STATE_IMAGE_REQUESTED = 5

    class Shadow(QGraphicsRectItem):
        pass

    class Box(QGraphicsRectItem):
        pass

    class Signals(QObject):
        image_prepared = pyqtSignal(QPixmap, float)

    def __init__(self, index, view: QGraphicsView, manager, renderer, ratio):
        super().__init__()
        self.words = None
        self.blocks = None
        self.number = None
        self.index = index
        self.manager = manager
        self.renderer = renderer
        self.signals2 = SimplePage.Signals()
        self.signals2.image_prepared.connect(self.image_ready)
        # self.renderer.image_ready.connect(self.image_ready)
        self.ratio = ratio
        self.view = view
        self.state = SimplePage.STATE_INVALID
        self.image = None
        self.w, self.h = self.renderer.get_page_size(index)
        self.rearrange_pickup_pose = None

        self.setRect(QRectF(0, 0, self.w, self.h))
        self.setAcceptTouchEvents(True)

        self.setBrush(Qt.white)
        self.setPen(Qt.transparent)
        self.lock = QMutex()

        self.box = self.Box(self)
        self.box.setRect(QRectF(0, 0, self.w, self.h))
        self.box.setBrush(QBrush(QColor(80, 80, 80, 80)))
        self.box.setVisible(False)
        # self.box.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        # Shadow
        brush = QBrush(QColor(80, 80, 80, 255))
        self.shadow_right = self.Shadow(self)
        self.shadow_right.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        self.shadow_right.setBrush(brush)
        self.shadow_right.setPen(Qt.transparent)

        self.shadow_bottom = self.Shadow(self)
        self.shadow_bottom.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.shadow_bottom.setBrush(brush)
        self.shadow_bottom.setPen(Qt.transparent)

        self.request_image_timer = QTimer()
        self.request_image_timer.setSingleShot(True)
        self.request_image_timer.timeout.connect(self.process_requested_image)
        self.requested_image_ratio = 1

        self.image_ratio = 0

    def get_index(self):
        return self.index

    def get_view(self):
        return self.view

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)

    def get_sep(self):
        return 10 + 17  # * self.get_scaling_ratio()

    def get_scaled_width(self):
        return self.get_orig_width() * self.get_scaling_ratio()

    def get_scaled_height(self):
        return self.get_orig_height() * self.get_scaling_ratio()

    def get_page_items(self, kind, strict=True):
        if strict:
            return reversed([p for p in self.childItems() if type(p) == kind])
        else:
            return reversed([p for p in self.childItems() if isinstance(p, kind)])

    def finish_setup(self):
        if self.view.is_fitting_width():
            self.fit_width()
        else:
            self.update_image(self.ratio)

    def update_image(self, ratio):
        # print("Updating image for page", self.index, "with ratio", ratio, "and state", self.state)
        # No need to do anything else, the paint called in
        # response to the scale method will take care of it
        self.ratio = ratio
        self.setTransform(QTransform(ratio, 0, 0, 0, ratio, 0, 0, 0, 1))
        self.state = SimplePage.STATE_INVALID
        # self.paint_accessories()

    def fit_width(self):
        width = self.view.width() - 50
        fit_ratio = width / self.get_orig_width()
        self.update_image(fit_ratio)
        return fit_ratio

    def compute_fit_width(self):
        width = self.view.width() - 50
        return width / self.get_orig_width()

    def get_scaling_ratio(self):
        return self.transform().m11()

    def request_image(self, ratio, now=False):
        self.requested_image_ratio = ratio
        self.request_image_timer.stop()
        self.request_image_timer.start(500 if not now else 5)

    def process_requested_image(self):
        if self.isShown():
            image = self.renderer.render_page(self.index, self.requested_image_ratio)
            self.image_ready(image, self.requested_image_ratio)

    def kk(self):
        print("inside kk")
        image = self.renderer.render_page(self.index, self.requested_image_ratio)
        print("image", image)
        self.signals2.image_prepared.emit(image, self.requested_image_ratio)
        print("emitted", image)

    def aprocess_requested_image(self):
        self.view.submit(self.kk)

    def paint(self, painter, option, widget: typing.Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)
        if True:  # self.state == SimplePage.STATE_INVALID or self.state == SimplePage.STATE_FORCED:
            # self.renderer.request_image(self.index, self.ratio, self.state == SimplePage.STATE_FORCED)
            if self.image is None or self.ratio != self.image_ratio:
                print('Requesting image for page', self.index, self.view)
                self.request_image(self.ratio, self.image is None)
                self.state = SimplePage.STATE_IMAGE_REQUESTED

        if self.image is not None:
            # self.lock.lock()
            painter.drawImage(QRectF(0, 0, self.rect().width(), self.rect().height()), self.image.toImage())
            # painter.drawPixmap(QPointF(0, 0), self.image, QRectF(0, 0, self.rect().width()/self.ratio, self.rect().height()/self.ratio))
            # self.lock.unlock()

    def image_ready(self, image, ratio):
        print("Image ready for page", self.index, "with state", self.state, "and image", image.width(), "x", image.height())
        self.image = image
        self.image_ratio = ratio
        self.state = SimplePage.STATE_FINAL
        if self.isShown():
            self.update()

    def image_ready2(self, index, ratio, image):
        if index == self.index:  # and ratio == self.ratio:
            self.image = image
            self.state = SimplePage.STATE_FINAL
            self.update()

    def invalidate(self):
        print('Invalidating page', self.index)
        self.state = self.STATE_FORCED
        self.image = None
        self.w, self.h = self.renderer.get_page_size(self.index)
        self.setRect(QRectF(0, 0, self.w, self.h))
        self.box.setRect(QRectF(0, 0, self.w, self.h))
        # self.paint_accessories()
        self.update()

    def get_orig_size(self):
        return self.w, self.h

    def get_orig_width(self):
        return self.get_orig_size()[0]

    def get_orig_height(self):
        return self.get_orig_size()[1]

    def paint_accessories(self):
        # Selection Box
        self.box.setRect(self.rect())
        self.box.setBrush(QBrush(QColor(128, 128, 128, 80)))

        # Shadow
        shadow_width = 10
        self.shadow_right.setRect(QRectF(self.get_scaled_width(), shadow_width, shadow_width, self.get_scaled_height()))
        self.shadow_bottom.setRect(
            QRectF(shadow_width, self.get_scaled_height(), self.get_scaled_width(), shadow_width))

    def mark(self, value, color=Qt.red):
        self.box.setPen(color)
        self.box.setVisible(value)

    def isMarked(self):
        return self.box.isVisible()

    def get_size(self):
        return self.rect().width(), self.rect().height()

    def visible_area(self):
        port_rect = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(port_rect).boundingRect()
        item_rect = self.mapRectFromScene(scene_rect)
        intersection = item_rect.intersected(self.boundingRect())
        return intersection.width() * intersection.height(), intersection

    def isShown(self):
        port_rect = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(port_rect).boundingRect()
        item_rect = self.mapRectFromScene(scene_rect)
        intersection = item_rect.intersected(self.boundingRect())
        return not intersection.isEmpty()

    def is_completely_shown(self):
        port_rect = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(port_rect).boundingRect()
        item_rect = self.mapRectFromScene(scene_rect)
        intersection = item_rect.intersected(self.boundingRect())
        if intersection.height() < self.rect().height() or intersection.width() < self.rect().width():
            return False
        return True

    def visibleRect(self):
        port_rect = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(port_rect).boundingRect()
        item_rect = self.mapRectFromScene(scene_rect)
        isec = item_rect.intersected(self.boundingRect())
        return isec

    def is_selected(self):
        return self.box.isVisible()

    def set_selected(self, true):
        print("Setting selected", true)
        self.box.setVisible(true)
