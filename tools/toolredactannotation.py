import base64

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QMenu, QDialog, QMessageBox

from annotations.redactannotation import RedactAnnotation
from dialogs import PasswordDialog
from renderer import convert_box_to_upside_down
from resizeable import ResizableRectItem
from signer import P12Signer
from tools.tool import Tool


class ToolRedactAnnotation(Tool):
    def __init__(self, view, renderer, config):
        super().__init__(view, renderer, config)
        self.rubberband = None

    def configure(self):
        pass

    def mouse_pressed(self, event):
        page = self.view.get_page_at_pos(event.pos())

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
            self.finished.emit()

    def finish(self):
        self.view.setCursor(Qt.ArrowCursor)
