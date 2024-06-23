from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem

from swik.simplepage import SimplePage


# from utils import Signals


class Page(SimplePage):
    class PageSignals(QObject):
        item_added = pyqtSignal(QGraphicsItem)

    def __init__(self, index, view, manager, renderer, ratio):
        self.signals = Page.PageSignals()
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

    def gather_words(self, force=False):
        if self.words is None or force:
            self.words = self.renderer.extract_words(self.index)
            for word in self.words:
                word.join(self)
        return self.words

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
