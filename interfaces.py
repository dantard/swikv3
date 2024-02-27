from PyQt5.QtCore import QObject, pyqtSignal


class Undoable:

    def __init__(self):
        self.callback = None

    def set_callback(self, callback):
        self.callback = callback

    def notify_change(self, old, new):
        if self.callback is not None:
            self.callback(self, old, new)

    def undo(self, info):
        raise NotImplementedError

    def redo(self, info):
        pass

class Serializable:

    def serialize(self, info):
        pass

    def deserialize(self, info):
        pass
