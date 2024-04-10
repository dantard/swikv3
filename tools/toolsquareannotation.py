import base64

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QMenu, QDialog, QMessageBox

from annotations.redactannotation import RedactAnnotation
from annotations.squareannotation import SquareAnnotation
from dialogs import PasswordDialog
from renderer import convert_box_to_upside_down
from resizeable import ResizableRectItem
from signer import P12Signer
from tools.tool import Tool


class ToolSquareAnnotation(Tool):
    def __init__(self, view, renderer, config):
        super().__init__(view, renderer, config)
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
