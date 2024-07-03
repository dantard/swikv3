import os
import importlib.resources as pkg_resources
from pathlib import Path

import psutil
from PyQt5.QtCore import QObject, pyqtSignal, QRectF, QRect, Qt, QTimer
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem, QHBoxLayout, QLabel, QSizePolicy, QFrame, QGroupBox, QVBoxLayout, QWidget, QMessageBox, QCheckBox
from pymupdf import pymupdf


class Signals(QObject):
    done = pyqtSignal(QGraphicsRectItem)
    moving = pyqtSignal(QGraphicsRectItem)
    resizing = pyqtSignal(QGraphicsRectItem)
    creating = pyqtSignal(QGraphicsRectItem)
    action = pyqtSignal(int, object)
    item_added = pyqtSignal(QGraphicsItem)
    item_removed = pyqtSignal(QGraphicsItem)
    item_changed = pyqtSignal(QGraphicsItem)
    discarded = pyqtSignal()


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
    return pymupdf.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())


def qrectf_and_pos_to_fitz_rect(rect, pos):
    return pymupdf.Rect(pos.x(), pos.y(), pos.x() + rect.width(), pos.y() + rect.height())


def qcolor_to_fitz_color(color: QColor):
    if color == Qt.transparent:
        return None
    return color.red() / 255, color.green() / 255, color.blue() / 255


def fitz_color_to_qcolor(color, opacity=1):
    color = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255),
                   int(opacity * 255)) if color else Qt.transparent
    return color


def adjust_crop(image: QImage, ratio=1.0) -> QRectF:
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
    return QRectF(left / ratio, top / ratio, (right - left) / ratio + 2, (bottom - top) / ratio + 2)
    # return QRect(left, top, right - left + 1, bottom - top + 1)/ratio


def are_other_instances_running():
    swiks = [p for p in psutil.process_iter() if len(p.cmdline()) > 1 and "swik" in p.cmdline()[1]]
    # And their PID
    pids = [p.pid for p in swiks]
    # Remove my PID
    pids.remove(os.getpid())
    # Remove all the swiks that are children (worker for the real swik)
    for swik in swiks:
        for p in swik.children():
            if p.pid in pids:
                pids.remove(p.pid)

    if len(pids) == 0:
        return -1
    else:
        swik = psutil.Process(pids[-1])
        # Get other instance port
        return swik.connections()[0][3][1]


def update_value(method, dictionary, key):
    method(dictionary[key] if key in dictionary else None)


def delayed(delay, func, *args):
    QTimer.singleShot(delay, lambda: func(*args))


def int_to_roman(number):
    num = [1, 4, 5, 9, 10, 40, 50, 90,
           100, 400, 500, 900, 1000]
    sym = ["I", "IV", "V", "IX", "X", "XL",
           "L", "XC", "C", "CD", "D", "CM", "M"]
    i = 12
    res = str()
    while number:
        div = number // num[i]
        number %= num[i]

        while div:
            res += sym[i]
            div -= 1
        i -= 1
    return res


colors = [Qt.black, Qt.red, Qt.green, Qt.blue, Qt.magenta, Qt.cyan, Qt.darkRed, Qt.darkGreen, Qt.darkBlue, ]


def get_color(index):
    return colors[index % len(colors)]


def row(w1, w2):
    h_layout = QHBoxLayout()
    if isinstance(w1, str):
        w1 = QLabel(w1)
        w1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    h_layout.addWidget(w1)
    h_layout.addWidget(w2)
    return h_layout, w1, w2


def col(w1, w2, *args):
    v_layout = QVBoxLayout()
    if isinstance(w1, str):
        w1 = QLabel(w1)
        w1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    v_layout.addWidget(w1)
    v_layout.addWidget(w2)
    for w in args:
        v_layout.addWidget(w)

    return v_layout


def separator():
    hLine = QFrame()
    hLine.setFrameShape(QFrame.HLine)
    hLine.setFrameShadow(QFrame.Sunken)
    return hLine


def framed(widget, title=None):
    frame = QGroupBox()
    frame.setStyleSheet(
        "QGroupBox {border: 1px solid silver; border-radius: 2px; margin-top: 10px;}"
        "QGroupBox::title { subcontrol-origin: margin;    left: 7px;  padding: 0px 5px 0px 5px;}")

    frame.setTitle(title if title else "")
    frame.setLayout(QVBoxLayout())

    if isinstance(widget, QWidget):
        frame.layout().addWidget(widget)
    else:
        frame.layout().addLayout(widget)

    return frame


def get_font_path(name):
    package_name = 'swik.fonts'
    return str(pkg_resources.path(package_name, name))


def get_warning_messagebox(text, parent=None):
    msg = QMessageBox()
    msg.setParent(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Yes)
    msg.addButton(QMessageBox.Cancel)
    # msg.setDefaultButton(QMessageBox.Cancel)

    check_box = QCheckBox("Don't show this again")
    msg.setCheckBox(check_box)
    return msg.exec() == QMessageBox.Yes, check_box.isChecked()
