from PyQt5.QtCore import QObject, pyqtSignal, QRectF
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
