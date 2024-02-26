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



    def die(self):
        self.dying = True
        self.update()
        super().die()
