import glob
import glob
import os
import shutil
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QPoint, QRectF
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMenu, QMessageBox, QFileDialog, QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QPushButton, QLabel, QGraphicsItem
from swik.annotations.redact_annotation import RedactAnnotation, Patch

from swik.interfaces import Copyable

from swik import utils

from swik.word import Word

from swik.simplepage import SimplePage

from swik.dialogs import ImportDialog
from swik.resizeable import ResizableRectItem
from swik.tools.tool import Tool


class InsertImageRectItem(ResizableRectItem, Copyable):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

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

    def duplicate(self):
        r = InsertImageRectItem(self.parentItem(), **self.kwargs)
        r.setRect(self.rect())
        r.setPos(self.pos() + QPointF(10, 10))
        return r, self.parentItem()


class ResizeableWidget(QWidget):
    resized = pyqtSignal()

    def resizeEvent(self, event):
        self.resized.emit()
        return super(ResizeableWidget, self).resizeEvent(event)


class ImageConf:
    def __init__(self, config, section_name, file=None):
        header = config.root().getSubSection("Images", "Images")
        self.image = header.getSubSection(section_name)
        self.stretch = self.image.getCombobox("stretch", pretty="Stretch", default=0, items=["Stretch", "Maintain Ratio", "Maintain Size"])
        self.image_file = self.image.getFile("file", pretty="Image File", extension=["png", "jpg", "jpeg", "bmp", "gif", "tiff", "tif"], extension_name="Image",
                                             default=file)


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
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
        # h_layout.addWidget(add_btn)

        # self.draw_btn = QPushButton("✎")
        # self.draw_btn.setFixedSize(25, 25)

        self.draw_btn = QPushButton("Draw")

        self.draw_btn.setEnabled(False)
        self.draw_btn.clicked.connect(self.draw_image)
        self.draw_btn.setCheckable(True)
        self.image_lb = ClickableLabel()
        self.image_lb.clicked.connect(self.on_image_clicked)

        # self.image_lb.setScaledContents(True)
        # self.image_lb.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        v_layout.setAlignment(Qt.AlignTop)
        # v_layout.addWidget(QLabel("Imported Images"))

        frame = utils.framed(h_layout, "Imported Images")
        v_layout.addWidget(frame)

        # v_layout.addWidget(QLabel("Image"))
        frame = utils.framed(self.image_lb, "Current Image")
        v_layout.addWidget(frame)

        self.save_btn = QPushButton("+")
        self.save_btn.setMaximumSize(25, 25)
        self.save_btn.clicked.connect(self.save_image)
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Import current image")

        self.discard_btn = QPushButton("×")
        self.discard_btn.setMaximumSize(25, 25)
        self.discard_btn.clicked.connect(self.discard_image)
        self.discard_btn.setEnabled(False)
        self.discard_btn.setToolTip("Discard image")

        hh_layout = QHBoxLayout()

        hh_layout.addWidget(self.save_btn)
        hh_layout.addWidget(self.discard_btn)
        hh_layout.addWidget(self.draw_btn)
        # hh_layout.setAlignment(Qt.AlignRight)
        v_layout.addLayout(hh_layout)

        raise_images_btn = QPushButton("Raise Image")
        raise_images_btn.clicked.connect(self.raise_images)
        frame = utils.framed(raise_images_btn, "Raise Image")
        # v_layout.addWidget(frame)

        # v_layout.addWidget(self.draw_btn)
        self.helper.setLayout(v_layout)
        self.widget.set_app_widget(self.helper, 250, title="Insert Image")

        self.update_cb()
        self.update_image()
        self.check_interaction()

    def discard_image(self):
        self.image_filename = None
        self.update_image()
        self.check_interaction()

    def save_image(self):
        import_dialog = ImportDialog("Select image", "JPG (*.jpg)", self.image_filename, Path(self.image_filename).stem)
        if import_dialog.exec_():
            nickname = import_dialog.get_nickname()
            self.images[nickname] = ImageConf(self.config, import_dialog.get_nickname(), import_dialog.get_file())
            self.nicknames.get_value().append(nickname)
            self.update_cb(True)

    def make_default(self):
        selected = self.image_cb.currentText()
        self.nicknames.get_value().remove(selected)
        self.nicknames.get_value().insert(0, selected)
        self.update_cb()
        self.check_interaction()

    def on_resize_event(self):
        self.update_image()

    def context_menu(self, event):
        pos_on_view = self.view.mapFromGlobal(event.globalPos())
        page = self.view.get_page_at_pos(pos_on_view)
        pos_on_scene = self.view.mapToScene(pos_on_view)
        pos_on_page = page.mapFromScene(pos_on_scene)
        pos_on_page = QPoint(int(pos_on_page.x()), int(pos_on_page.y()))

        images = self.renderer.get_images(page.index)

        selected = None
        for image, x, y, rect in images:
            rect_on_page = QRectF(x, y, rect.width(), rect.height())
            if rect_on_page.contains(pos_on_page):
                selected = (image, x, y, rect)

        if selected is not None:
            image, x, y, rect = selected
            menu = QMenu()
            move_action = menu.addAction("Move Image")
            remove_action = menu.addAction("Remove Image")
            save_action = menu.addAction("Save Image")
            res = menu.exec(event.globalPos())
            if res == move_action:
                patch = Patch(page)
                patch.setRect(QRectF(0, 0, rect.width() + 2, rect.height() + 2))
                patch.setPos(x - 1, y - 1)

                item = InsertImageRectItem(self.view.pages[0], pen=Qt.transparent, brush=Qt.transparent, image=image, image_mode=self.image_mode)
                item.setRect(rect)
                item.setPos(x, y)
                item.setZValue(100)
            elif res == remove_action:
                patch = Patch(page)
                patch.setRect(QRectF(0, 0, rect.width() + 2, rect.height() + 2))
                patch.setPos(x - 1, y - 1)
            elif res == save_action:
                filename, _ = QFileDialog.getSaveFileName(None, "Save Image", "", "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif)")
                if filename:
                    image.save(filename)

    def raise_images(self):
        images = self.renderer.get_images(0)
        for image, x, y, rect in images:
            patch = Patch(self.view.pages[0])
            patch.setRect(rect)
            patch.setPos(x, y)

            item = InsertImageRectItem(self.view.pages[0], pen=Qt.transparent, brush=Qt.transparent, image=image, image_mode=self.image_mode)
            item.setRect(rect)
            item.setPos(x, y)
            item.setZValue(100)

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
        if self.image_cb.currentIndex() >= 1:
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
        self.discard_btn.setEnabled(self.image_filename is not None)
        self.save_btn.setEnabled(self.image_filename is not None)
        self.draw_btn.setEnabled(self.image_filename is not None)

    def on_image_changed(self):

        if self.image_cb.currentIndex() > 0:
            if image := self.images.get(self.image_cb.currentText()):
                self.image_filename = image.image_file.get_value()
                self.image_mode = image.stretch.get_value()
                self.draw_btn.setEnabled(True)
        else:
            self.image_filename = None
            self.image_mode = None
            self.draw_btn.setEnabled(False)
            self.save_btn.setEnabled(False)

        self.update_image()
        self.check_interaction()

    def update_image(self):
        if self.image_filename is not None:
            self.image_lb.setPixmap(QPixmap(self.image_filename).scaledToWidth(self.helper.width() - 20, Qt.SmoothTransformation))
            self.image_lb.setText("")
            self.image_lb.setContentsMargins(0, 0, 0, 0)

            self.save_btn.setEnabled(True)
            for image in self.images.values():
                if image.image_file.get_value() == self.image_filename:
                    self.save_btn.setEnabled(False)
                    break
        else:
            self.image_lb.setText("Click to load a new image\nor select an imported image\nabove")
            self.image_lb.setContentsMargins(0, 50, 0, 50)
            self.image_lb.setAlignment(Qt.AlignCenter)

        self.check_interaction()

    def mouse_pressed(self, event):
        if self.view.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return

        page = self.view.get_page_at_pos(event.pos())
        if page is None:
            return

        if self.rubberband is not None:
            if self.rubberband.parentItem() is None:
                self.rubberband.setParentItem(page)
                self.rubberband.notify_creation()
                self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)

    def draw_image(self):
        if self.rubberband is None:
            self.rubberband = InsertImageRectItem(None, pen=Qt.transparent, brush=Qt.transparent, image_filename=self.image_filename,
                                                  image_mode=self.image_mode)
            self.rubberband.signals.done.connect(self.selection_done)
            self.view.viewport().setCursor(Qt.CrossCursor)

    def selection_done(self, rb):
        if rb.get_rect_on_parent().width() > 5 and rb.get_rect_on_parent().height() > 5:
            pass
        else:
            self.view.scene().removeItem(rb)

        self.draw_btn.setChecked(False)
        self.draw_btn.setEnabled(True)
        self.view.viewport().setCursor(Qt.ArrowCursor)
        self.rubberband = None

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
