import typing

import fitz
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QRectF, Qt, QRect, QPointF, pyqtSignal, QObject, QPoint, QTimer
from PyQt5.QtGui import QColor, QBrush, QPen, QPixmap, QImage, QFont, QFontMetrics
from PyQt5.QtWidgets import QGraphicsRectItem, QWidget, QGraphicsItem, QGraphicsPixmapItem, QMenu, QGraphicsView, QColorDialog, QDialog, QInputDialog, \
    QFileDialog

from SwikItems import SwikRectItem


class RubberBand(SwikRectItem):
    TEXT_MODE_STRETCH = 0
    TEXT_MODE_KEEP = 1
    IMAGE_MODE_STRETCH = 2
    IMAGE_MODE_MAINTAIN_RATIO = 3
    IMAGE_MODE_DONT_MAINTAIN_RATIO = 4
    IMAGE_MODE_MAINTAIN_SIZE = 5

    params = ['brush', 'pen', 'image', 'textmode', 'imagemode',
              'text', 'textpen', 'font', 'maxfontsize', 'cursor', 'filter']

    class Signals(QObject):
        ready = pyqtSignal(QGraphicsRectItem)
        button_clicked = pyqtSignal(QGraphicsRectItem, bool)
        moving = pyqtSignal(QGraphicsRectItem)

    def __init__(self, view, parent: QGraphicsRectItem = None, **kwargs):
        super(RubberBand, self).__init__(parent, False)

        self.init_pos_item = None
        self.filter = None
        if not set(kwargs).issubset(self.params):
            raise Exception("One or more of the parameters do not exist")
        self.ok_button = None
        self.ko_button = None
        self.cursor_pointer = None
        self.signals = self.Signals()
        self.max_font_size = None
        self.stay_into_parent = False
        self.init_pos = None
        self.view = view
        self.image = None
        self.text = None
        self.text_mode = None
        self.image_file = None
        self.text_pen = None
        self.font = None
        self.pdf_document = None
        self.moving_handle = None
        self.image_mode = RubberBand.IMAGE_MODE_MAINTAIN_SIZE
        self.kwargs = kwargs
        self.set_config(**kwargs)

    def stop_timer(self):
        if self.interaction_frame is not None:
            self.interaction_frame.timer.stop()

    def serialize(self):
        self.kwargs['pos'] = self.pos()
        self.kwargs['rect'] = self.rect()
        self.kwargs['page_index'] = self.get_target_item().index
        self.kwargs['has_interaction_frame'] = self.interaction_frame is not None
        return self.kwargs

    def deserialize(self, **kwargs):
        index = kwargs.pop("page_index")
        page = self.view.pages[index]
        self.setRect(kwargs.pop('rect'))
        self.init_pos_item = page
        self.setParentItem(self.init_pos_item)
        self.setPos(kwargs.pop('pos'))
        if kwargs.pop('has_interaction_frame'):
            self.add_interaction_frame()
        self.set_config(**kwargs)

    def set_target_item(self, page):
        self.init_pos_item = page
        self.setParentItem(page)

    def get_image_file(self):
        return self.image_file

    def set_config(self, **kwargs):
        self.filter = kwargs.get('filter')
        brush = kwargs.get('brush', QBrush(QColor(80, 80, 80, 80)))
        pen = kwargs.get('pen', QPen(Qt.transparent))
        self.image = kwargs.get('image', None)
        self.text = kwargs.get('text', None)
        self.text_mode = kwargs.get('textmode', self.TEXT_MODE_STRETCH)
        self.image_mode = kwargs.get('imagemode', self.IMAGE_MODE_MAINTAIN_RATIO)
        self.text_pen = kwargs.get('textpen', QPen(Qt.black))
        self.font = kwargs.get('font', QFont("Courier New"))
        self.max_font_size = kwargs.get('maxfontsize', 25)
        self.cursor_pointer = kwargs.get('cursor', Qt.ArrowCursor)
        self.view.viewport().setCursor(self.cursor_pointer)
        self.setBrush(brush)
        self.setPen(pen)

    def paint(self, painter: QtGui.QPainter, option, widget: typing.Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)

        # if self.init_pos is None:
        #    return

        if self.image is not None:
            if self.image_mode == self.IMAGE_MODE_MAINTAIN_RATIO:
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
            elif self.image_mode == self.IMAGE_MODE_STRETCH:
                painter.drawImage(QPointF(self.rect().x(), self.rect().y()), self.image, QRectF(0, 0, self.rect().width(), self.rect().height()))
            elif self.image_mode == self.IMAGE_MODE_DONT_MAINTAIN_RATIO:
                painter.drawImage(self.rect(), self.image)
            elif self.image_mode == self.IMAGE_MODE_MAINTAIN_SIZE:
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

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseMoveEvent(event)
        on_view = self.view.mapFromScene(event.scenePos())
        self.mouse_move(on_view)

    def mouse_press(self, pos):

        if self.filter is not None:
            self.init_pos_item = self.view.get_items_at_pos(pos, self.filter, 0, False)
            if self.init_pos_item is None:
                return

        self.setParentItem(self.init_pos_item)
        on_scene = self.view.mapToScene(pos)
        if self.init_pos_item is not None:
            self.init_pos = self.init_pos_item.mapFromScene(on_scene)
        else:
            self.init_pos = on_scene

        self.setRect(QRectF(0, 0, 0, 0))
        self.setPos(self.init_pos)
        self.setVisible(True)

    def set_filter(self, kind):
        self.filter = kind

    def get_filter(self):
        return self.filter

    def mouse_move(self, pos):
        if self.init_pos is not None:
            pos_on_scene = self.view.mapToScene(pos)
            if self.init_pos_item is not None:
                pos_on_item = self.init_pos_item.mapFromScene(pos_on_scene)
                x, y = pos_on_item.x(), pos_on_item.y()

                if self.init_pos_item is not None:
                    x = self.init_pos_item.rect().x() if x < self.init_pos_item.rect().x() else x
                    x = self.init_pos_item.rect().x() + self.init_pos_item.rect().width() if x > self.init_pos_item.rect().x() + self.init_pos_item.rect().width() else x
                    y = self.init_pos_item.rect().y() if y < self.init_pos_item.rect().y() else y
                    y = self.init_pos_item.rect().y() + self.init_pos_item.rect().height() if y > self.init_pos_item.rect().y() + self.init_pos_item.rect().height() else y
            else:
                x, y = pos_on_scene.x(), pos_on_scene.y()

            rect = QRectF(0, 0, x - self.init_pos.x(), y - self.init_pos.y()).normalized()

            if self.image_mode != self.IMAGE_MODE_MAINTAIN_SIZE:
                self.setRect(rect)
            else:
                self.setRect(QRectF(0, 0, self.image.width(), self.image.height()))
            self.setPos(self.init_pos.x(), self.init_pos.y())

            self.update()
            self.signals.moving.emit(self)

    def mouse_release(self, pos):
        if self.init_pos is not None:
            self.init_pos = None

            x, y = self.rect().x(), self.rect().y()

            self.setRect(QRectF(0, 0, self.rect().width(), self.rect().height()))
            if x < 0:
                self.setPos(self.pos().x() - self.rect().width(), self.pos().y())
            if y < 0:
                self.setPos(self.pos().x(), self.pos().y() - self.rect().height())

            self.emit_ready()

    def emit_ready(self):
        self.signals.ready.emit(self)

    def get_scene_rect(self):
        return self.sceneBoundingRect()

    def get_target_item_rect(self, adjust_to_image=False):
        if self.init_pos_item is not None:
            return self.mapRectToItem(self.init_pos_item, self.rect())
        return None

    def get_target_item_image_rect(self):
        if self.init_pos_item is not None:
            if self.image_mode == self.IMAGE_MODE_MAINTAIN_RATIO:
                rw, rh = self.rect().width(), self.rect().height()
                iw, ih = self.image.width(), self.image.height()
                if rw != 0 and iw != 0 and ih != 0:
                    ratio = rw / iw if rh / rw > ih / iw else rh / ih
                    rect = QRectF(self.rect().x(), self.rect().y(), iw * ratio, ih * ratio)
                else:
                    rect = self.rect()
            elif self.image_mode == self.IMAGE_MODE_MAINTAIN_SIZE:
                rect = QRectF(self.rect().x(), self.rect().y(), self.image.width(), self.image.height())
            elif self.image_mode == self.IMAGE_MODE_STRETCH:
                rect = QRectF(0, 0, self.rect().width(), self.rect().height())
            elif self.image_mode == self.IMAGE_MODE_DONT_MAINTAIN_RATIO:
                rect = self.rect()

            return self.mapRectToItem(self.init_pos_item, rect)

    def get_image_file(self):
        return self.image_file

    def get_view_rect(self):
        return self.view.mapFromScene(self.sceneBoundingRect())

    def reset(self):
        self.init_pos = None
        self.setVisible(False)

    def finish(self):
        self.view.viewport().setCursor(Qt.ArrowCursor)
        self.scene().removeItem(self)

    def get_target_item(self):
        return self.init_pos_item


class StaticRubberBand(RubberBand):

    def __init__(self, view, parent: QGraphicsRectItem = None, **kwargs):
        super(StaticRubberBand, self).__init__(view, parent, **kwargs)
        self.acceptTouchEvents()
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        # self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        # self.handle = InteractionFrame(self)
        self.hovering = False
        self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mousePressEvent(event)
        self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.OpenHandCursor)

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseMoveEvent(event)
        x = max(0, self.pos().x())
        x = min(x, self.parentItem().rect().width() - self.rect().width())
        y = max(0, self.pos().y())
        y = min(y, self.parentItem().rect().height() - self.rect().height())
        self.setPos(x, y)
        # self.handle.display()

    def emit_ready(self):
        super().emit_ready()

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        super().contextMenuEvent(event)
        event.accept()
        menu = QMenu()
        delete = menu.addAction("Delete")
        duplicate = menu.addAction("Duplicate")
        res = menu.exec_(event.screenPos())
        if res == delete:
            self.scene().removeItem(self)
        elif res == duplicate:
            self.scene().views()[0].duplicate(self)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        super().hoverLeaveEvent(event)

    def paint(self, painter: QtGui.QPainter, option, widget: typing.Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)


class AnonymizerRubberBand(StaticRubberBand):
    def __init__(self, view, parent: QGraphicsRectItem = None, **kwargs):
        super().__init__(view, parent, **kwargs)
        # self.handle.set_enable_resize(True)

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        a = QColorDialog(self.brush().color())
        if a.exec_() == QDialog.Accepted:
            self.setBrush(QBrush(a.selectedColor()))
            self.update()


class ImageRubberBand(StaticRubberBand):
    def __init__(self, view, parent: QGraphicsRectItem = None, **kwargs):
        super().__init__(view, parent, **kwargs)

    def emit_ready(self):
        super().emit_ready()

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        event.accept()
        menu = QMenu()
        maintain_size = menu.addAction("Set Maintain Size")
        maintain_ratio = menu.addAction("Set Maintain Ratio")
        stretch = menu.addAction("Set Stretch")
        menu.addSeparator()
        download = menu.addAction("Download")
        if self.image is not None:
            menu.addSeparator()
            move = menu.addAction("Move to page")
        menu.addSeparator()
        duplicate = menu.addAction("Duplicate")
        menu.addSeparator()
        delete = menu.addAction("Delete")

        res = menu.exec_(event.screenPos())
        if res == delete:
            self.scene().removeItem(self)
        elif res == maintain_size:
            self.image_mode = self.IMAGE_MODE_MAINTAIN_SIZE
            self.update()
        elif res == maintain_ratio:
            self.image_mode = self.IMAGE_MODE_MAINTAIN_RATIO
            self.update()
        elif res == stretch:
            self.image_mode = self.IMAGE_MODE_DONT_MAINTAIN_RATIO
            self.update()
        elif res == move:
            index, ok = QInputDialog.getInt(self.view, "Move to page", "Page", self.get_target_item().index + 1, 1, len(self.view.pages))
            print(index, ok, "kaka")
            if ok:
                self.set_target_item(self.view.pages[index - 1])
        elif res == download:
            dest, ext = IOManager.get_save_dialog("Save image", "PNG File (*.png);;JPG File (*.jpg)", "download_image")
            if dest is not None and dest != "":
                if not dest.endswith(ext):
                    dest += ext
                self.image.save(dest)
        elif res == duplicate:
            self.view.duplicate(self)


class SignatureRubberBand(StaticRubberBand):

    def __init__(self, view, parent: QGraphicsRectItem = None, **kwargs):
        super().__init__(view, parent, **kwargs)

    def add_interaction_frame(self):
        super().add_interaction_frame()
        self.interaction_frame.set_enabled(True, True, True)
        self.interaction_frame.accept.signals.clicked.connect(self.accepted)

    def accepted(self):
        self.signals.button_clicked.emit(self, True)

    def emit_ready(self):
        super().emit_ready()
