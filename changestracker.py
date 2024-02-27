from PyQt5.QtCore import QObject

from action import Action, CreateAction
from annotations.redactannotation import RedactAnnotation
from interfaces import Undoable
from simplepage import SimplePage


# This is just an undo/redo class; the philosophy is the following:
# It manages directly undo/redo of creation and removal of items, and it is the only one that can do it.
# Instead, the items are responsible for their own changes, and they notify the changes to the tracker
# through the notify_change method. They send an Action object, that contains the item, the kind of change,
# and the old and new state of the item. These states can be anything but must mean something to the item since
# they will be sent back by the tracker by calling undo() and redo() and the item must restore its state accordingly.
# The actions are stored to implement the undone or redone. The states are vectors of atoms because they can store
# multiple changes at once, for example when a word is replaced, it is covered by a redaction and a new word is added
# which are 2 atoms to undo/redo. The items that want to be undoable must implement the Undoable interface.

class ChangesTracker(QObject):

    def __init__(self, view):
        super().__init__()
        self.undo_stack = []
        self.redo_stack = []
        self.view = view

    def undo(self):
        print("undo stack", len(self.undo_stack))
        if len(self.undo_stack) > 0:
            action = self.undo_stack.pop()
            self.redo_stack.append(action)
            for atom in action:
                if atom.kind == Action.ACTION_CREATE:
                    self.view.scene().removeItem(atom.item)
                elif atom.kind == Action.ACTION_REMOVE:
                    if atom.old is not None:
                        atom.item.setParentItem(atom.old)
                    else:
                        self.view.scene().addItem(atom.item)
                else:
                    atom.item.undo(atom.kind, atom.old)

    def redo(self):
        print("redo stack", len(self.redo_stack))
        if len(self.redo_stack) > 0:
            action = self.redo_stack.pop()
            for atom in action:
                if atom.kind == Action.ACTION_CREATE:
                    if atom.old is not None:
                        atom.item.setParentItem(atom.old)
                    else:
                        self.view.scene().addItem(atom.item)
                elif atom.kind == Action.ACTION_REMOVE:
                    self.view.scene().removeItem(atom.item)
                else:
                    atom.item.redo(atom.kind, atom.new)
            self.undo_stack.append(action)

    def item_added(self, item):
        if isinstance(item, SimplePage):
            item.signals.item_added.connect(self.item_added)
        elif isinstance(item, Undoable):
            item.set_callback(self.item_changed)
            self.undo_stack.append(Action(item, Action.ACTION_CREATE, item.parentItem()))

    def item_removed(self, item):
        if isinstance(item, Undoable):
            item.set_callback(self.item_changed)
            self.undo_stack.append(Action(item, Action.ACTION_REMOVE, item.parentItem()))

    def item_changed(self, action):
        self.undo_stack.append(action)
