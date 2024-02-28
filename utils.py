import fitz
from PyQt5.QtCore import QObject, pyqtSignal, QRectF, QRect, Qt
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem


class Signals(QObject):
    done = pyqtSignal(QGraphicsRectItem)
    moving = pyqtSignal(QGraphicsRectItem)
    resizing = pyqtSignal(QGraphicsRectItem)
    creating = pyqtSignal(QGraphicsRectItem)
    action = pyqtSignal(int, object)
    item_added = pyqtSignal(QGraphicsItem)
    item_removed = pyqtSignal(QGraphicsItem)
    item_changed = pyqtSignal(QGraphicsItem)
    mierda_changed = pyqtSignal(int)


def check_parent_limits(parent: QGraphicsRectItem, scene_x, scene_y):
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


def fitz_rect_to_qrectf(rect):
    return QRectF(rect.x0, rect.y0, rect.x1 - rect.x0, rect.y1 - rect.y0)


def qrectf_to_fitz_rect(rect):
    return fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())


def qcolor_to_fitz_color(color: QColor):
    return color.red() / 255, color.green() / 255, color.blue() / 255


def adjust_crop(image: QImage) -> QRect:
    # Create a QColor object to represent white
    white = QColor(Qt.white)

    # Initialize variables for the dimensions of the smallest rectangle
    # that contains non-white pixels
    left = image.width()
    top = image.height()
    right = 0
    bottom = 0

    # Iterate over all pixels in the image
    for x in range(image.width()):
        for y in range(image.height()):
            # Get the color of the current pixel
            color = QColor(image.pixel(x, y))

            # If the color is not white, update the dimensions of the
            # smallest rectangle that contains non-white pixels
            if color != white:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    # Return the smallest rectangle that contains non-white pixels
    return QRect(left, top, right - left + 1, bottom - top + 1)
