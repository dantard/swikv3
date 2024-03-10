from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem

from changestracker import ChangesTracker
from utils import Signals


class Scene(QGraphicsScene):

    def __init__(self):
        super().__init__()
        self.signals = Signals()
        self.changes_tracker = ChangesTracker(self)

    def tracker(self) -> ChangesTracker:
        return self.changes_tracker
    
    def addItem(self, item) -> None:
        super().addItem(item)
        self.signals.item_added.emit(item)

    def removeItem(self, item) -> None:
        super().removeItem(item)
        if item is not None:
            self.signals.item_removed.emit(item)
