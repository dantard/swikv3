import typing
from PyQt5 import QtGui
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QWidget, QGraphicsRectItem

from rect import SwikRect


class PaintableRectItem(SwikRect):
    TEXT_MODE_STRETCH = 0
    TEXT_MODE_KEEP = 1
    IMAGE_MODE_STRETCH = 3
    IMAGE_MODE_MAINTAIN_RATIO = 1
    IMAGE_MODE_MAINTAIN_SIZE = 2

    def __init__(self, parent=None, **kwargs):
        super(PaintableRectItem, self).__init__(parent, **kwargs)
        self.image_mode = kwargs.get("image_mode", self.IMAGE_MODE_MAINTAIN_RATIO)
        self.image = kwargs.get("image", None)
        self.text = kwargs.get("text", "")
        self.text_mode = kwargs.get("text_mode", self.TEXT_MODE_STRETCH)
        self.max_font_size = kwargs.get("max_font_size", 100)
        self.font = kwargs.get("font", QFont("Arial", 12))
        self.dying = False

    def paint(self, painter: QtGui.QPainter, option, widget: typing.Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)

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
                painter.drawImage(self.rect(), self.image)
            elif self.image_mode == self.IMAGE_MODE_MAINTAIN_SIZE:
                w = min(self.rect().width(), self.image.width())
                h = min(self.rect().height(), self.image.height())
                img = self.image.copy(0, 0, int(w), int(h))
                painter.drawImage(QRectF(self.rect().x(), self.rect().y(), w, h), img)

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

    def die(self):
        self.dying = True
        self.update()
        super().die()
