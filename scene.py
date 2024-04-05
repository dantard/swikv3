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
        self.bunches = []
        self.prev_selection = []
        # self.selectionChanged.connect(self.selection_changed)

    '''
    def selection_changed(self):
        for elem in self.prev_selection:
            try:
                elem.signals.font_changed.disconnect(self.font_changed)
            except:
                pass
        for elem in self.selectedItems():
            elem.signals.font_changed.connect(self.font_changed)

        self.prev_selection = self.selectedItems()
    '''

    def font_changed(self, item):
        for elem in self.selectedItems():
            elem.setFont(item.font())

    def tracker(self) -> ChangesTracker:
        return self.changes_tracker

    def addItem(self, item) -> None:
        super().addItem(item)
        self.signals.item_added.emit(item)

    def removeItem(self, item) -> None:
        super().removeItem(item)
        if item is not None:
            self.signals.item_removed.emit(item)

    def remove_bunches(self, kind):
        bunches = [b for b in self.bunches if type(b) == kind]
        for bunch in bunches:
            self.bunches.remove(bunch)

    def keyPressEvent(self, event) -> None:
        items = self.selectedItems()
        if len(items) == 0:
            super().keyPressEvent(event)
        elif event.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]:
            val = 1 if event.modifiers() == QtCore.Qt.ControlModifier else 10
            if event.key() == QtCore.Qt.Key_Up:
                x, y = 0, -1
            elif event.key() == QtCore.Qt.Key_Down:
                x, y = 0, 1
            elif event.key() == QtCore.Qt.Key_Left:
                x, y = -1, 0
            elif event.key() == QtCore.Qt.Key_Right:
                x, y = 1, 0
            else:
                x, y = 0, 0

            for item in items:
                item.moveBy(x * val, y * val)
        elif event.key() == QtCore.Qt.Key_Delete:
            self.delete_objects()
        elif event.key() == QtCore.Qt.Key_Backspace:
            self.delete_objects()
        else:
            super().keyPressEvent(event)

    def delete_objects(self):
        items = self.selectedItems()
        self.tracker().items_removed(items)
        for item in items:
            self.removeItem(item)

    def keyReleaseEvent(self, event) -> None:
        return
