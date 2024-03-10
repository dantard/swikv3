from PyQt5.QtCore import QObject

from action import Action, CreateAction
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
    def __init__(self, scene):
        super(ChangesTracker, self).__init__()
        self.undo_stack = []
        self.redo_stack = []
        self.scene = scene

    def set_view(self, view):
        self.scene = scene

    def undo(self):
        print("undo stack", len(self.undo_stack))
        if len(self.undo_stack) > 0:
            action = self.undo_stack.pop()
            self.redo_stack.append(action)
            for atom in action:
                if atom.kind == Action.ACTION_CREATE:
                    self.scene.removeItem(atom.item)
                elif atom.kind == Action.ACTION_REMOVE:
                    if atom.old is not None:
                        print("set parent", atom.item, atom.old, "undo remove")
                        atom.item.setParentItem(atom.old)
                    else:
                        self.scene.addItem(atom.item)
                else:
                    atom.item.undo(atom.kind, atom.old)

    def redo(self):
        print("redo stack", len(self.redo_stack))
        if len(self.redo_stack) > 0:
            action = self.redo_stack.pop()
            for atom in action:
                print("item redo", atom.item, atom.kind, atom.old, atom.new)
                if atom.kind == Action.ACTION_CREATE:
                    if atom.old is not None:
                        atom.item.setParentItem(atom.old)
                    else:
                        self.scene.addItem(atom.item)
                elif atom.kind == Action.ACTION_REMOVE:
                    self.scene.removeItem(atom.item)
                else:
                    atom.item.redo(atom.kind, atom.new)
            self.undo_stack.append(action)

    def item_added(self, item):
        self.undo_stack.append(Action(item, Action.ACTION_CREATE, item.parentItem()))
        print("item added", item)

    def item_removed(self, item):
        self.undo_stack.append(Action(item, Action.ACTION_REMOVE, item.parentItem()))
        print("item removed", item, item.parentItem())

    def items_removed(self, items):
        action = Action()
        for item in items:
            action.push(item, Action.ACTION_REMOVE, item.parentItem())
        self.undo_stack.append(action)

    def item_changed(self, action):
        print("item changed", action[0].item, action[0].kind, action[0].old, action[0].new)
        self.undo_stack.append(action)
