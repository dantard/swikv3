from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem

from simplepage import SimplePage
from utils import Signals


class Page(SimplePage):
    def __init__(self, index, view, manager, renderer, ratio):
        self.signals = Signals()
        super().__init__(index, view, manager, renderer, ratio)
        self.words = None
        self.info = QGraphicsTextItem(self)
        self.info.setPlainText(str(index))
        font = self.info.font()
        font.setPixelSize(40)
        self.info.setFont(font)
        self.info.setVisible(False)
        self.info.setFlag(QGraphicsItem.ItemIgnoresTransformations)

    def toggle_info(self):
        self.info.setVisible(not self.info.isVisible())

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)

    def set_words(self, words, join=True):
        self.words = words
        for word in self.words:
            word.join(self)
        # self.renderer.fill_font_info(self.index, self.words)

    def has_words(self):
        return self.words is not None

    def get_words(self):
        return self.words

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemChildAddedChange:
            self.signals.item_added.emit(value)
        return super().itemChange(change, value)

    def invalidate(self):
        super().invalidate()
        if self.words is not None:
            for word in self.words:
                self.scene().removeItem(word)
            self.words = None
