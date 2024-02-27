from PyQt5.QtCore import QObject, pyqtSignal

from action import Action


class Undoable:

    def __init__(self):
        self.callback = None

    def set_callback(self, callback):
        self.callback = callback

    def notify_change(self, kind, old, new):
        if self.callback is not None:
            self.callback(Action(self, kind, old, new))

    def undo(self, kind, info):
        raise NotImplementedError

    def redo(self, kind, info):
        pass


class Serializable:

    def serialize(self, info):
        pass

    def deserialize(self, info):
        pass
