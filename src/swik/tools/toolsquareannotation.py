from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from swik.annotations.squareannotation import SquareAnnotation
from swik.tools.tool import Tool


class ToolSquareAnnotation(Tool):
    def __init__(self, widget):
        super().__init__(widget)
        self.rubberband = None

    def configure(self):
        pass

    def mouse_pressed(self, event):
        page = self.view.over_a_page(event)

        if page is None:
            return

        if self.rubberband is None:
            color = QColor(255, 0, 0, 127)
            self.rubberband = SquareAnnotation(page, pen=color, brush=color)
            self.rubberband.view_mouse_press_event(self.view, event)
            self.rubberband.notify_creation()
            self.view.setCursor(Qt.CrossCursor)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)
            self.rubberband = None

    def finish(self):
        self.view.setCursor(Qt.ArrowCursor)
