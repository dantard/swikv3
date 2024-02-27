from PyQt5.QtCore import QObject

from annotations.redactannotation import RedactAnnotation
from interfaces import Undoable
from simplepage import SimplePage


class ChangesTracker(QObject):

    def __init__(self):
        super().__init__()
        self.undo_stack = []
        self.redo_stack = []

    def undo(self):
        print("undo stack", len(self.undo_stack))
        if len(self.undo_stack) > 0:
            item, old, new = self.undo_stack.pop()
            self.redo_stack.append((item, old, new))
            item.undo(old)

    def redo(self):
        print("redo stack", len(self.redo_stack))
        if len(self.redo_stack) > 0:
            item, old, new = self.redo_stack.pop()
            item.redo(new)
            self.undo_stack.append((item, old, new))

    def item_added(self, object):
        print("itemsadded2222", object, type(object))
        if isinstance(object, SimplePage):
            print("connecting2222")
            object.signals.item_added.connect(self.item_added)
        elif isinstance(object, Undoable):
            print("connecting", object)
            object.set_callback(self.item_changed)

    def item_removed(self, object):
        print("item removed", object)

    def item_changed(self, item, old, new):
        print("append to stack", len(self.undo_stack))
        self.undo_stack.append((item, old, new))
