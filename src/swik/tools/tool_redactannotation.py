from PyQt5.QtCore import Qt

from swik.annotations.redact_annotation import RedactAnnotation
from swik.tools.tool import Tool


class ToolRedactAnnotation(Tool):
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
            self.rubberband = RedactAnnotation(page, pen=Qt.transparent, brush=RedactAnnotation.initial_color)
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
            # self.finished.emit()

    def finish(self):
        self.view.setCursor(Qt.ArrowCursor)
