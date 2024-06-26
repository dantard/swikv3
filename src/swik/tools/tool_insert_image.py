import glob
import glob
import os
import shutil

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMenu, QMessageBox, QFileDialog, QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QPushButton, QLabel

from swik.dialogs import ImportDialog
from swik.resizeable import ResizableRectItem
from swik.tools.tool import Tool


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
        menu.addSeparator()
        delete = menu.addAction("Delete")

        res = menu.exec(event.screenPos())
        if res == stretch:
            self.set_image_mode(self.IMAGE_MODE_STRETCH)
        elif res == maintain_ratio:
            self.set_image_mode(self.IMAGE_MODE_MAINTAIN_RATIO)
        elif res == maintain_size:
            self.set_image_mode(self.IMAGE_MODE_MAINTAIN_SIZE)
        elif res == delete:
            self.notify_deletion(self)
            self.scene().removeItem(self)
        self.update()


class ToolInsertImage(Tool):
    configured = False
    signature = None

    @staticmethod
    def configure(config):
        if not ToolInsertImage.configured:
            section = config.root().addSubSection("Image Signature")
            ToolInsertImage.signature = section.addFile("image_image", pretty="Signature File", extension=["png", "jpg"], extension_name="Image")
            ToolInsertImage.configured = True

    def __init__(self, widget):
        super().__init__(widget)
        self.rubberband = None
        self.image = None
        self.image_filename = None

    def init(self):
        filename, _ = QFileDialog.getOpenFileName(None, "Select image", "", "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif)")
        if filename:
            self.image = QImage(filename)
            self.image_filename = filename
        else:
            self.emit_finished()

    def mouse_pressed(self, event):
        page = self.view.get_page_at_pos(event.pos())

        if page is None:
            return

        if self.rubberband is None:
            self.rubberband = InsertImageRectItem(page, pen=Qt.transparent, brush=Qt.transparent, image_filename=self.image_filename, image_mode=3)
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
            self.view.setCursor(Qt.ArrowCursor)
            self.emit_finished()

    def finish(self):
        self.view.setCursor(Qt.ArrowCursor)


class ResizeableWidget(QWidget):
    resized = pyqtSignal()

    def resizeEvent(self, event):
        self.resized.emit()
        return super(ResizeableWidget, self).resizeEvent(event)


class ImageConf:
    def __init__(self, config, section_name, file=None):
        header = config.root().getSubSection("images", "Images")
        self.image = header.getSubSection(section_name)
        self.stretch = self.image.getCombobox("stretch", pretty="Stretch", default=0, items=["Stretch", "Maintain Ratio", "Maintain Size"])
        self.image_file = self.image.getFile("file", pretty="Image File", extension=["png", "jpg", "jpeg", "bmp", "gif", "tiff", "tif"], extension_name="Image",
                                             default=file)


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        print("clicked")
        super(ClickableLabel, self).mousePressEvent(event)
        self.clicked.emit()


class ToolInsertSignatureImage(Tool):
    def __init__(self, widget):
        super().__init__(widget)
        self.image_cb = None
        self.draw_btn = None
        self.signature = None
        self.rubberband = None
        self.helper = None
        self.images = {}
        self.image_filename = None
        self.image_mode = None

        self.nicknames = self.config.root().getList("image_list", default=[], hidden=True)
        self.config.read()

        self.configure()

    def init(self):

        self.helper = ResizeableWidget()
        self.helper.resized.connect(self.on_resize_event)
        v_layout = QVBoxLayout()

        self.image_cb = QComboBox()
        self.image_cb.setMinimumWidth(120)
        self.image_cb.currentIndexChanged.connect(self.on_image_changed)
        h_layout = QHBoxLayout()

        self.make_default_btn = QPushButton("☑")
        self.make_default_btn.clicked.connect(self.make_default)
        self.make_default_btn.setFixedSize(25, 25)
        self.make_default_btn.setToolTip("Make default")

        add_btn = QPushButton("+")
        add_btn.clicked.connect(self.import_image)
        add_btn.setFixedSize(25, 25)
        add_btn.setToolTip("Add image")

        self.remove_btn = QPushButton("-")
        self.remove_btn.clicked.connect(self.remove_image)
        self.remove_btn.setFixedSize(25, 25)
        self.remove_btn.setToolTip("Remove")

        self.config_btn = QPushButton("⚙")
        self.config_btn.clicked.connect(self.show_config)
        self.config_btn.setFixedSize(25, 25)
        self.config_btn.setToolTip("Configure")

        h_layout.addWidget(self.image_cb)
        # h_layout.addWidget(self.make_default_btn)
        h_layout.addWidget(self.config_btn)
        h_layout.addWidget(self.remove_btn)
        h_layout.addWidget(add_btn)

        self.draw_btn = QPushButton("Draw")
        self.draw_btn.setEnabled(False)
        self.draw_btn.clicked.connect(self.draw_image)
        self.draw_btn.setCheckable(True)
        self.image_lb = ClickableLabel()
        self.image_lb.clicked.connect(self.on_image_clicked)

        # self.image_lb.setScaledContents(True)
        # self.image_lb.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        v_layout.setAlignment(Qt.AlignTop)
        v_layout.addWidget(QLabel("Imported Images"))
        v_layout.addLayout(h_layout)
        v_layout.addWidget(QLabel("Image"))
        v_layout.addWidget(self.image_lb)

        v_layout.addWidget(self.draw_btn)
        self.helper.setLayout(v_layout)
        self.widget.set_app_widget(self.helper, title="Insert Image")

        self.update_cb()
        self.update_image()
        self.check_interaction()

    def make_default(self):
        selected = self.image_cb.currentText()
        self.nicknames.get_value().remove(selected)
        self.nicknames.get_value().insert(0, selected)
        self.update_cb()
        self.check_interaction()

    def on_resize_event(self):
        self.update_image()

    def configure(self):
        self.images.clear()

        for nickname in self.nicknames.get_value():
            sc = ImageConf(self.config, nickname)
            self.images[nickname] = sc

        self.config.read()

    def update_cb(self, goto_last=False):
        self.image_cb.clear()
        self.image_cb.addItem("Not Selected")
        self.image_cb.addItems(self.nicknames.get_value())
        self.check_interaction()
        if goto_last:
            self.image_cb.setCurrentIndex(self.image_cb.count() - 1)

    def import_image(self):
        import_dialog = ImportDialog("Select image", "JPG (*.jpg)")
        if import_dialog.exec_():
            nickname = import_dialog.get_nickname()
            self.images[nickname] = ImageConf(self.config, import_dialog.get_nickname(), import_dialog.get_file())
            self.nicknames.get_value().append(nickname)
            self.update_cb(True)

    def remove_image(self):
        if self.image_cb.currentIndex() > 1:
            index = self.image_cb.currentText()
            ask = QMessageBox.question(self.helper, "Remove Image", "Are you sure you want to remove this image?", QMessageBox.Yes | QMessageBox.No)
            if ask == QMessageBox.Yes:
                self.images.pop(index)
                self.nicknames.get_value().remove(index)
                self.update_cb()

    def get_selected(self):
        index = self.image_cb.currentText()
        return self.images.get(index, None)

    def show_config(self):
        self.config.exec(self.images[self.image_cb.currentText()].image)
        self.on_image_changed()

    def check_interaction(self):
        self.remove_btn.setEnabled(self.image_cb.currentIndex() > 0)
        self.config_btn.setEnabled(self.image_cb.currentIndex() > 0)
        self.make_default_btn.setEnabled(self.image_cb.currentIndex() > 1)

    def on_image_changed(self):

        if self.image_cb.currentIndex() > 0:
            image = self.images[self.image_cb.currentText()]
            self.image_filename = image.image_file.get_value()
            self.image_mode = image.stretch.get_value()
            self.draw_btn.setEnabled(True)
        else:
            self.image_filename = None
            self.image_mode = None
            self.draw_btn.setEnabled(False)

        self.update_image()
        self.check_interaction()

    def update_image(self):
        if self.image_filename is not None:
            self.image_lb.setPixmap(QPixmap(self.image_filename).scaledToWidth(self.helper.width() - 20, Qt.SmoothTransformation))
            self.image_lb.setText("")
            self.image_lb.setContentsMargins(0, 0, 0, 0)
        else:
            self.image_lb.setText("Click to load image or\nselect imported image\nabove")
            self.image_lb.setContentsMargins(0, 100, 0, 100)
            self.image_lb.setAlignment(Qt.AlignCenter)

    def mouse_pressed(self, event):
        page = self.view.get_page_at_pos(event.pos())
        if page is None:
            return

        if self.rubberband is not None:
            if self.rubberband.parentItem() is None:
                self.rubberband.setParentItem(page)
                self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            if self.rubberband.view_mouse_release_event(self.view, event):
                self.draw_btn.setChecked(False)
                self.draw_btn.setEnabled(True)

            self.rubberband = None
        self.view.viewport().setCursor(Qt.ArrowCursor)

    def draw_image(self):
        if self.rubberband is None:
            self.rubberband = InsertImageRectItem(None, pen=Qt.transparent, brush=Qt.transparent, image_filename=self.image_filename,
                                                  image_mode=self.image_mode)
            self.view.viewport().setCursor(Qt.CrossCursor)

    def on_image_clicked(self):
        if self.image_filename is None:
            file_path, _ = QFileDialog.getOpenFileName(None, "Select image", "", "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif)")
            if file_path:
                self.image_filename = file_path
                self.image_mode = 0
                self.draw_btn.setEnabled(True)
                self.update_image()

    def finish(self):
        if self.rubberband is not None:
            self.view.scene().removeItem(self.rubberband)
            self.rubberband = None
        self.view.viewport().setCursor(Qt.ArrowCursor)
        self.widget.remove_app_widget()
        self.helper.deleteLater()
