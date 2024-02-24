from PyQt5.QtCore import Qt

from resizeable import ResizableRectItem
from selector import SelectorRectItem, PaintableSelectorRectItem
from simplepage import SimplePage
from tool import Tool
from word import Word


class ToolSign(Tool):
    def __init__(self, view, renderer):
        super().__init__(view, renderer)
        self.rubberband = None

    def mouse_pressed(self, event):
        page = self.view.get_page_at_pos(event.pos())
        if page is None:
            return

        if self.rubberband is None:
            self.rubberband = ResizableRectItem(page, text="Sign here")
            self.view.setCursor(Qt.CrossCursor)
            self.rubberband.signals.done.connect(self.process)
            self.view.scene().addItem(self.rubberband)
            self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)
            self.rubberband = None

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def process(self):

        self.finished.emit()

    def done(self):
        self.view.setCursor(Qt.ArrowCursor)
