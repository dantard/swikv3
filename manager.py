from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QGraphicsRectItem

from interfaces import Copyable
from simplepage import SimplePage
from word import Word


class Manager(QObject):
    tool_finished = pyqtSignal()

    def __init__(self, renderer, config):
        super(Manager, self).__init__()
        self.tools = {}
        self.default = None
        self.current = None
        self.config = config
        self.view: QGraphicsRectItem = None
        self.renderer = renderer
        self.copy_buffer = []

    def set_view(self, view):
        self.view = view

    def keyboard(self, action):
        if action == "Ctrl+C":
            self.copy_buffer.clear()
            items = self.view.scene().selectedItems()
            if len(items) == 0:
                self.current.keyboard("Ctrl+C")
            else:
                for item in items:
                    if isinstance(item, Copyable):
                        r, parent = item.duplicate()
                        self.copy_buffer.append((r, parent))
        elif action == "Ctrl+V":
            self.view.scene().clearSelection()
            for r, parent in self.copy_buffer:
                # self.view.scene().addItem(r)
                r.setParentItem(parent)
                r.setSelected(True)
        else:
            self.current.keyboard(action)

    def register_tool(self, name, tool, default=False):
        self.tools[name] = tool
        tool.finished.connect(self.finished)
        tool.configure()
        if default:
            self.default = tool
            self.use_tool(name)

    def get_tool(self, name):
        return self.tools[name]

    def use_tool(self, name):
        if self.current is not None:
            self.current.finish()
        self.current = self.tools[name]
        self.current.init()

    def mouse_pressed(self, event):
        # TODO:if not self.top_is(event.pos(), [SimplePage, SimplePage.MyImage, Word]):
        # return
        # if event.modifiers() & Qt.ShiftModifier:

        if self.current is not None:
            self.current.mouse_pressed(event)

    def mouse_released(self, event):
        if self.current is not None:
            self.current.mouse_released(event)

    def mouse_moved(self, event):
        if self.current is not None:
            self.current.mouse_moved(event)

    def mouse_double_clicked(self, event):
        if self.current is not None:
            self.current.mouse_double_clicked(event)

    def context_menu(self, event):
        if self.current is not None:
            self.current.context_menu(event)

    def key_pressed(self, event):
        print("pressed", event.key())

    def key_released(self, event):
        print("released", event.key(), Qt.Key_Escape, Qt.Key_Escape == event.key())

        if event.key() == Qt.Key_Escape:
            self.finished()

    def finished(self):
        self.tool_finished.emit()
