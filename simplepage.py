import typing

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPointF, QObject, QPoint, QThread
from PyQt5.QtGui import QBrush, QColor, QFontMetrics, QTransform, QPen
from PyQt5.QtWidgets import QWidget, QGraphicsPixmapItem, \
    QGraphicsView, QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem, QMenu

import MuPDFRenderer


class SimplePage(QGraphicsRectItem):
    STATE_BLANK = 0
    STATE_WAITING_FINAL = 1
    STATE_FINAL = 2
    STATE_INVALID = 3

    class MyImage(QGraphicsPixmapItem):
        def paint(self, painter: QtGui.QPainter, option: 'QStyleOptionGraphicsItem', widget: QWidget) -> None:
            super().paint(painter, option, widget)

    def __init__(self, index, view: QGraphicsView, manager, renderer, ratio):
        super().__init__()
        self.words = None
        self.blocks = None
        self.number = None
        self.index = index
        self.manager = manager
        self.renderer: MuPDFRenderer = renderer
        self.ratio = ratio
        self.view = view
        # self.setAcceptHoverEvents(True)
        self.setAcceptTouchEvents(True)
        self.w, self.h = self.renderer.get_page_size(index)
        self.setRect(QRectF(0, 0, self.w, self.h))
        self.state = SimplePage.STATE_INVALID
        self.rectangle = None
        self.rubberband = None
        self.rearrange_pickup_pose = None

        # self.setAcceptHoverEvents(True)
        self.setAcceptTouchEvents(True)
        self.shadow_right = QGraphicsRectItem(self)
        self.shadow_right.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.shadow_bottom = QGraphicsRectItem(self)
        self.shadow_bottom.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.image = self.MyImage(self)
        self.image.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.image.setVisible(False)
        self.box = QGraphicsRectItem(self)
        self.box.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setBrush(Qt.white)
        self.setPen(Qt.transparent)

        # Shadow
        brush = QBrush(QColor(80, 80, 80, 255))
        self.shadow_right.setBrush(brush)
        self.shadow_right.setPen(Qt.transparent)
        self.shadow_bottom.setBrush(brush)
        self.shadow_bottom.setPen(Qt.transparent)
        self.box.setVisible(False)
        self.setSelected(False)
        self.setAcceptDrops(True)
        self.paint_accessories()

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

    def connect_signals(self):
        self.renderer.image_ready.connect(self.image_ready)
        self.renderer.page_updated.connect(self.page_updated)

    def finish_setup(self):
        if self.view.is_fitting_width():
            self.fit_width()
        else:
            self.update_image(self.ratio)

    def update_image(self, ratio):
        # No need to do anything else, the paint called in
        # response to the scale method will take care of it
        self.ratio = ratio
        self.setTransform(QTransform(ratio, 0, 0, 0, ratio, 0, 0, 0, 1))
        self.image.setVisible(False)
        self.state = SimplePage.STATE_INVALID
        self.paint_accessories()

    def fit_width(self):
        width = self.view.width() - 50
        fit_ratio = width / self.get_orig_width()
        self.update_image(fit_ratio)

    def get_scaling_ratio(self):
        return self.transform().m11()

    def paint(self, painter, option, widget: typing.Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)
        if self.state == SimplePage.STATE_INVALID:
            image, final = self.renderer.request_image(self.index, self.ratio, 0)
            self.state = SimplePage.STATE_FINAL if final else SimplePage.STATE_WAITING_FINAL
            self.image.setVisible(True)
            self.image.setPixmap(image)
            self.image.update()
        elif self.state == SimplePage.STATE_WAITING_FINAL:
            self.state = SimplePage.STATE_FINAL

    def image_ready(self, index, ratio, key, pixmap):
        if index == self.index and key == 0 and ratio == self.ratio:
            self.image.setScale(1)
            self.image.setPixmap(pixmap)
            self.image.setVisible(True)

    def invalidate(self):
        self.state = self.STATE_INVALID
        self.w, self.h = self.renderer.get_page_size(self.index)
        self.setRect(QRectF(0, 0, self.w, self.h))
        self.paint_accessories()
        self.update()

    def get_orig_size(self):
        return self.w, self.h

    def get_orig_width(self):
        return self.get_orig_size()[0]

    def get_orig_height(self):
        return self.get_orig_size()[1]

    def paint_accessories(self):
        # Selection Box
        self.box.setRect(QRectF(-5, -5, self.get_scaled_width() + 10, self.get_scaled_height() + 10))
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

    def page_updated(self, index):
        if index == self.index:
            self.invalidate()
        # BEFORE: self.invalidate()
        # self.paint_accessories()

    def is_selected(self):
        return self.box.isVisible()

    def set_selected(self, true):
        self.box.setVisible(true)
