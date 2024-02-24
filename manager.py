from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QGraphicsRectItem

from simplepage import SimplePage
from word import Word


class Manager(QObject):
    tool_finished = pyqtSignal()

    def __init__(self, renderer):
        super(Manager, self).__init__()
        self.tools = {}
        self.default = None
        self.current = None
        self.view: QGraphicsRectItem = None
        self.renderer = renderer

    def set_view(self, view):
        self.view = view

    def add_tool(self, name, tool, default=False):
        self.tools[name] = tool
        tool.finished.connect(self.finished)
        if default:
            self.default = tool
            self.use_tool(name)

    def get_tool(self, name):
        return self.tools[name]

    def use_tool(self, name):
        if self.current is not None:
            self.current.done()
        self.current = self.tools[name]

    def top_is(self, pos, check_items):
        items = self.view.scene().items(self.view.mapToScene(pos))
        print(items)
        if len(items) == 0:
            return False
        for item in check_items:
            if isinstance(items[0], item):
                return True
        return False

    def mouse_pressed(self, event):
        if not self.top_is(event.pos(), [SimplePage, SimplePage.MyImage, Word]):
            return

        if self.current is not None:
            self.current.mouse_pressed(event)

    def mouse_released(self, event):
        if self.current is not None:
            self.current.mouse_released(event)

    def mouse_moved(self, event):
        if self.current is not None:
            self.current.mouse_moved(event)

    def context_menu(self, event):
        if self.current is not None:
            self.current.context_menu(event)

    def finished(self):
        self.tool_finished.emit()
