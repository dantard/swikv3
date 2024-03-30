import base64

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QMenu, QDialog, QMessageBox, QFileDialog

from annotations.redactannotation import RedactAnnotation
from dialogs import PasswordDialog
from renderer import convert_box_to_upside_down
from resizeable import ResizableRectItem
from signer import P12Signer
from tools.tool import Tool


class InsertImageRectItem(ResizableRectItem):
    def contextMenuEvent(self, event):
        menu = QMenu()
        image_mode = self.get_image_mode()
        stretch = menu.addAction("Set Mode Stretch")
        stretch.setCheckable(True)
        stretch.setChecked(image_mode == self.IMAGE_MODE_STRETCH)
        maintain_ratio = menu.addAction("Set Mode Maintain Ratio")
        maintain_ratio.setCheckable(True)
        maintain_ratio.setChecked(image_mode == self.IMAGE_MODE_MAINTAIN_RATIO)
        maintain_size = menu.addAction("Set Mode Maintain Size")
        maintain_size.setCheckable(True)
        maintain_size.setChecked(image_mode == self.IMAGE_MODE_MAINTAIN_SIZE)
        res = menu.exec(event.screenPos())
        if res == stretch:
            self.set_image_mode(self.IMAGE_MODE_STRETCH)
        elif res == maintain_ratio:
            self.set_image_mode(self.IMAGE_MODE_MAINTAIN_RATIO)
        elif res == maintain_size:
            self.set_image_mode(self.IMAGE_MODE_MAINTAIN_SIZE)
        self.update()


class ToolInsertImage(Tool):
    configured = False
    signature = None

    @staticmethod
    def configure(config):
        if not ToolInsertImage.configured:
            section = config.root().addSubSection("Image Signature")
            ToolInsertImage.signature = section.addFile("image_signature", pretty="Signature File", extension=["png", "jpg"], extension_name="Image")
            ToolInsertImage.configured = True

    def __init__(self, view, renderer, config):
        super().__init__(view, renderer, config)
        self.rubberband = None
        self.image = None

    def init(self):
        filename, _ = QFileDialog.getOpenFileName(None, "Select image", "", "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif)")
        if filename:
            self.image = QImage(filename)

    def mouse_pressed(self, event):
        page = self.view.get_page_at_pos(event.pos())

        if page is None:
            return

        if self.rubberband is None:
            self.rubberband = InsertImageRectItem(page, pen=Qt.transparent, brush=Qt.transparent, image=self.image, image_mode=3)
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


class ToolInsertSignatureImage(ToolInsertImage):
    def init(self):
        self.image = QImage(ToolInsertImage.signature.get_value())

    def usable(self):
        return ToolInsertImage.signature.get_value() is not None
