from PyQt5 import QtCore
from PyQt5.QtWidgets import QGraphicsScene

from swik.action import Action
from swik.changes_tracker import ChangesTracker
from swik.utils import Signals


class Scene(QGraphicsScene):

    def __init__(self):
        super().__init__()
        self.signals = Signals()
        self.changes_tracker = ChangesTracker(self)
        self.bunches = []
        self.selectionChanged.connect(self.selection_changed)
        self.group = None
        self.poses = {}

    def get_bunches_count(self):
        return len(self.bunches)

    def notify_change(self, item, kind, old, new):
        action = Action(item, kind, old, new)
        self.tracker().item_changed(action)
        full_state = item.get_full_state()
        for elem in self.selectedItems():
            if elem is not item and type(elem) == type(item):
                old = elem.get_full_state()
                elem.set_common_state(full_state)
                action.push(elem, kind, old, elem.get_full_state())

    def notify_any_change(self, kind, item, old, new):
        action = Action(item, kind, old, new)

        for elem in self.selectedItems():
            if elem is not item and elem in self.poses and elem.pos() != self.poses[elem]:
                action.push(elem, kind, self.poses[elem], elem.pos())

        self.tracker().item_changed(action)

    def notify_position_change(self, item, old, new):
        action = Action(item, Action.POSE_CHANGED, old, new)

        for elem in self.selectedItems():
            if elem is not item and elem in self.poses and elem.pos() != self.poses[elem]:
                action.push(elem, Action.POSE_CHANGED, self.poses[elem], elem.pos())

        self.tracker().item_changed(action)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        # print("mouse press on scene", event.scenePos())
        super(Scene, self).mousePressEvent(event)

    def selection_changed(self):
        self.poses.clear()
        for elem in self.selectedItems():
            self.poses[elem] = elem.pos()

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
            print("eooo")
            super().keyPressEvent(event)
            if event.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]:
                if event.key() in [QtCore.Qt.Key_Right, QtCore.Qt.Key_Up]:
                    view = self.views()[0]
                    view.move_to_page(view.page + 1)
                elif event.key() in [QtCore.Qt.Key_Down, QtCore.Qt.Key_Left]:
                    view = self.views()[0]
                    view.move_to_page(view.page - 1)

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
                pre = item.pos()
                item.setPos(item.pos().x() + x * val, item.pos().y() + y * val)
                self.notify_position_change(item, pre, item.pos())
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
            if hasattr(item, "deleted"):
                item.deleted()
            self.removeItem(item)

    def keyReleaseEvent(self, event) -> None:
        super(Scene, self).keyReleaseEvent(event)

    # TODO: to be completed
    '''
    def context_menu(self, event):
        items = self.selectedItems()
        if len(items) == 1:
            intersection = items[0].get_full_state().keys()
        else:
            intersection = None
            for item in self.selectedItems():
                state = item.get_common_state().keys()
                intersection = list(set(state) & set(intersection)) if intersection is not None else state

        print("intersection", intersection)
        menu = QMenu()
        edit = menu.addAction("Edit", self.delete_objects)
        delete = menu.addAction("Delete", self.delete_objects)
        res = menu.exec(event.screenPos())
        if res == edit:
            dialog = ComposableDialog()
            for row in intersection:
                if row == "brush":
                    dialog.add_row("Brush", Color(self.brush().color()))
    '''
