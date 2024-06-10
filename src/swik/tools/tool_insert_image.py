import glob
import glob
import os
import shutil

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMenu, QMessageBox, QFileDialog, QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QPushButton, QLabel

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
            self.emit_finished()

    def finish(self):
        self.view.setCursor(Qt.ArrowCursor)


class ResizeableWidget(QWidget):
    resized = pyqtSignal()

    def resizeEvent(self, event):
        self.resized.emit()
        return super(ResizeableWidget, self).resizeEvent(event)


class SignatureConf:
    def __init__(self, header, section_name, file):
        self.image = header.getSubSection(section_name)
        self.nickname = self.image.getString("nickname", pretty="Nickname", default=section_name)
        self.stretch = self.image.getCombobox("stretch", pretty="Stretch", default=0, items=["Stretch", "Maintain Ratio", "Maintain Size"])
        self.image_file = file


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
        self.signature_filename = None
        self.rubberband = None
        self.helper = None
        self.images = []
        self.image_filename = None
        self.image_mode = None
        self.configure()

    def init(self):

        self.helper = ResizeableWidget()
        self.helper.resized.connect(self.on_resize_event)
        v_layout = QVBoxLayout()

        self.image_cb = QComboBox()
        self.image_cb.currentIndexChanged.connect(self.on_image_changed)
        h_layout = QHBoxLayout()

        add_btn = QPushButton("+")
        add_btn.clicked.connect(self.import_image)
        add_btn.setFixedSize(25, 25)

        self.remove_btn = QPushButton("-")
        self.remove_btn.clicked.connect(self.remove_image)
        self.remove_btn.setFixedSize(25, 25)

        self.config_btn = QPushButton("⚙")
        self.config_btn.clicked.connect(self.show_config)
        self.config_btn.setFixedSize(25, 25)

        h_layout.addWidget(self.image_cb)
        h_layout.addWidget(self.config_btn)
        h_layout.addWidget(self.remove_btn)
        h_layout.addWidget(add_btn)

        self.draw_btn = QPushButton("Draw")
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
        self.widget.set_app_widget(self.helper, title="Sign")
        self.update_cb()

        self.update_image()
        self.check_interaction()

    def on_resize_event(self):
        self.update_image()

    def configure(self):
        self.images.clear()
        header = self.config.root().getSubSection("signature_images", pretty="Image Signatures")
        for file_path in glob.glob(os.path.join(self.config.base_dir + "images", '*.jpg')):
            if os.path.isfile(file_path):
                ic = SignatureConf(header, os.path.basename(file_path), file_path)
                self.images.append(ic)

        self.config.read()

    def update_cb(self):
        self.image_cb.clear()
        self.image_cb.addItem("Not Selected")
        self.image_cb.addItems([ic.nickname.get_value() for ic in self.images])

    def import_image(self):
        if not self.config.been_warned("image_import"):
            if QMessageBox.warning(self.helper, "Import signature",
                                   "The file will be copied to the signatures folder in the configuration directory.",
                                   QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return

        file_path, _ = QFileDialog.getOpenFileName(None, "Select image", "", "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif)")
        if file_path:
            self.config.set_warned("image_import", True)
            shutil.copy2(file_path, self.config.base_dir + "images")
            self.configure()
            self.update_cb()
            self.check_interaction()

    def remove_image(self):
        index = self.image_cb.currentIndex()
        if index >= 0:
            ask = QMessageBox.question(self.helper, "Remove signature", "Are you sure you want to remove this signature?", QMessageBox.Yes | QMessageBox.No)
            if ask == QMessageBox.Yes:
                # os.remove(self.cfg_p12[index])
                self.configure()
                self.image_cb.clear()
                # self.signature_cb.addItems([os.path.basename(p12).rstrip(".p12") for p12 in self.cfg_p12])
                self.check_interaction()

    def show_config(self):
        selected = self.image_cb.currentIndex() - 1
        self.config.exec(self.images[selected].image)
        index = self.image_cb.currentIndex()
        self.update_cb()
        self.image_cb.setCurrentIndex(index)

    def check_interaction(self):
        self.remove_btn.setEnabled(self.image_cb.currentIndex() > 0)
        self.config_btn.setEnabled(self.image_cb.currentIndex() > 0)

    def on_image_changed(self, index):
        if index > 0:
            self.image_filename = self.images[index - 1].image_file
            self.image_mode = self.images[index - 1].stretch.get_value()
        else:
            self.image_filename = None
            self.image_mode = None

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
                self.view.setCursor(Qt.ArrowCursor)

            self.rubberband = None

    def draw_image(self):

        if self.rubberband is None:
            self.rubberband = InsertImageRectItem(None, pen=Qt.transparent, brush=Qt.transparent, image_filename=self.image_filename,
                                                  image_mode=self.image_mode)
            self.view.setCursor(Qt.CrossCursor)

    def on_image_clicked(self):
        if self.image_filename is None:
            file_path, _ = QFileDialog.getOpenFileName(None, "Select image", "", "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif)")
            if file_path:
                self.image_filename = file_path
                self.image_mode = 0
                self.update_image()

    def finish(self):
        if self.rubberband is not None:
            self.view.scene().removeItem(self.rubberband)
            self.view.setCursor(Qt.ArrowCursor)
            self.rubberband = None
        self.view.setCursor(Qt.ArrowCursor)
        self.widget.remove_app_widget()
        self.helper.deleteLater()
