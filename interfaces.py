from PyQt5.QtCore import QObject, pyqtSignal

from action import Action
from changestracker import ChangesTracker


class Undoable:

    def notify_creation(self, item=None):
        ChangesTracker.item_added(item if item is not None else self)

    def notify_change(self, kind, old, new):
        if old != new:
            ChangesTracker.item_changed(Action(self, kind, old, new))

    def undo(self, kind, info):
        pass

    def redo(self, kind, info):
        pass


class Serializable:

    def serialize(self, info):
        pass

    def deserialize(self, info):
        pass
