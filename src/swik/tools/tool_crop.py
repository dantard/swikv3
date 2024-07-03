from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QMenu, QComboBox, QApplication, QMessageBox, QCheckBox

from swik import utils
from swik.action import Action
from swik.annotations.annotation import Annotation
from swik.annotations.hyperlink import Link
from swik.annotations.redact_annotation import RedactAnnotation
from swik.interfaces import Undoable
from swik.resizeable import ResizableRectItem
from swik.selector import SelectorRectItem
from swik.simplepage import SimplePage
from swik.tools.tool import Tool
from swik.word import Word


class Clearer(RedactAnnotation):
    pass


class CropRectItem(ResizableRectItem):
    ADJUST = 0
    CROP = 1
    ADJUST_N_CROP = 2

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        menu = QMenu()
        adjust = menu.addAction("Adjust Crop")
        crop = menu.addAction("Crop")
        adjust_and_crop = menu.addAction("Adjust and Crop")
        menu.addSeparator()
        discard = menu.addAction("Discard")
        res = menu.exec(event.screenPos())
        if res == discard:
            self.signals.discarded.emit()
        elif res == adjust:
            self.signals.action.emit(CropRectItem.ADJUST, None)
        elif res == crop:
            self.signals.action.emit(CropRectItem.CROP, None)
        elif res == adjust_and_crop:
            self.signals.action.emit(CropRectItem.ADJUST_N_CROP, None)


class ToolCrop(Tool, Undoable):

    def __init__(self, widget):
        super(ToolCrop, self).__init__(widget)
        self.rubberband = None

        (self.helper,
         self.vlayout,
         self.draw_btn,
         self.crop_btn,
         self.adjust_crop_btn,
         self.uncrop_btn,
         self.cropped_cb) = None, None, None, None, None, None, None

    def init(self):
        self.helper = QWidget()
        self.vlayout = QVBoxLayout()
        self.helper.setLayout(self.vlayout)
        self.draw_btn = QPushButton("Draw")
        self.draw_btn.setCheckable(True)
        self.draw_btn.clicked.connect(self.draw)

        self.crop_btn = QPushButton("Crop")
        self.crop_btn.clicked.connect(self.do_crop)

        self.adjust_crop_btn = QPushButton("Adjust Crop")
        self.adjust_crop_btn.clicked.connect(self.adjust_crop)

        self.uncrop_btn = QPushButton("Uncrop")
        self.uncrop_btn.clicked.connect(self.uncrop)

        self.clear_btn = QPushButton("Clean")
        self.clear_btn.clicked.connect(self.clear_cropped)

        self.cropped_cb = QComboBox()
        self.update_cropped()

        self.crop_btn.setEnabled(False)
        self.adjust_crop_btn.setEnabled(False)
        self.uncrop_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)

        self.vlayout.addWidget(utils.framed(utils.col(self.draw_btn, self.adjust_crop_btn, self.clear_btn, self.crop_btn), "Crop"))
        self.vlayout.addWidget(utils.framed(utils.col(self.cropped_cb, self.uncrop_btn), "Cropped pages"))

        self.widget.set_app_widget(self.helper, 180, "Crop")

    def clear_cropped(self):
        if not self.config.should_continue("clear_cropped44", "This action in not undoable.\nContinue?"):
            return

        page = self.rubberband.parentItem()
        self.renderer.add_redact_annot(page.index, QRectF(0, 0, self.rubberband.pos().x() - 1, page.rect().height()))
        self.renderer.add_redact_annot(page.index, QRectF(0, 0, page.rect().width(), self.rubberband.pos().y() - 1))
        self.renderer.add_redact_annot(page.index, QRectF(self.rubberband.pos().x() + self.rubberband.rect().width(), 0,
                                                          page.rect().width() - self.rubberband.pos().x() - self.rubberband.rect().width(),
                                                          page.rect().height()))
        self.renderer.add_redact_annot(page.index, QRectF(0, self.rubberband.pos().y() + self.rubberband.rect().height(), page.rect().width(),
                                                          page.rect().height() - self.rubberband.pos().y() - self.rubberband.rect().height()))
        page.invalidate()

    def draw(self):
        self.rubberband = CropRectItem(None, pen=Qt.transparent, brush=QColor(0, 0, 0, 80))
        self.rubberband.signals.done.connect(self.selection_done)
        self.rubberband.signals.discarded.connect(self.discarded)
        self.rubberband.signals.action.connect(self.actions)

    def update_cropped(self):
        self.cropped_cb.clear()
        for index in self.view.pages:
            if self.renderer.is_cropped(index):
                self.cropped_cb.addItem(str(index + 1))
        self.uncrop_btn.setEnabled(self.cropped_cb.count() > 0)

    def uncrop(self):
        index = int(self.cropped_cb.currentText()) - 1
        self.renderer.uncrop(index)
        self.update_cropped()

    def adjust_crop(self):
        page = self.rubberband.parentItem()
        if page is not None:
            rect = self.rubberband.get_rect_on_parent()
            image = page.get_image_by_rect(rect)
            rect2 = utils.adjust_crop(image.toImage(), page.image_ratio)
            rect3 = QRectF(rect.x() + rect2.x(), rect.y() + rect2.y(), rect2.width(), rect2.height())
            self.rubberband.setRect(QRectF(0, 0, rect3.width(), rect3.height()))
            self.rubberband.setPos(rect3.x(), rect3.y())

    def mouse_pressed(self, event):
        if event.button() == Qt.RightButton:
            return

        if self.view.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return

        page = self.view.get_page_at_pos(event.pos())

        if page is None:
            return

        if self.rubberband is not None:
            self.view.setCursor(Qt.CrossCursor)
            self.rubberband.setParentItem(page)
            self.rubberband.view_mouse_press_event(self.view, event)

    def discarded(self):
        self.crop_btn.setEnabled(False)
        self.adjust_crop_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.draw_btn.setEnabled(True)
        self.draw_btn.setChecked(False)

        self.view.scene().removeItem(self.rubberband)
        self.rubberband = None

    def actions(self, action, data):
        if action == CropRectItem.ADJUST:
            self.adjust_crop()
        elif action == CropRectItem.CROP:
            self.do_crop()
        elif action == CropRectItem.ADJUST_N_CROP:
            self.adjust_crop()
            self.do_crop()

    def selection_done(self, rb):
        if rb.get_rect_on_parent().width() > 5 and rb.get_rect_on_parent().height() > 5:
            self.crop_btn.setEnabled(True)
            self.adjust_crop_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
            self.draw_btn.setChecked(False)
            self.draw_btn.setEnabled(False)
        else:
            self.discarded()

    def do_crop(self):
        # Remove items outside the cropbox or move those inside
        page = self.rubberband.parentItem()
        items = self.view.pages[page.index].items((Link, Annotation, RedactAnnotation))
        for item in items:
            if not self.rubberband.get_rect_on_parent().contains(item.pos()):
                self.view.scene().removeItem(item)
            else:
                item.setPos(item.pos().x() - self.rubberband.get_rect_on_parent().x(), item.pos().y() - self.rubberband.get_rect_on_parent().y())

        # Apply the cropbox
        before = self.renderer.get_cropbox(page.index)
        self.renderer.set_cropbox(page.index, self.rubberband.get_rect_on_parent(), False)
        after = self.renderer.get_cropbox(page.index)
        self.notify_any_change(Action.ACTION_CHANGED, (page.index, before, 1), (page.index, after, 1), self.view.scene())

        self.view.scene().removeItem(self.rubberband)
        self.rubberband = None
        self.crop_btn.setEnabled(False)
        self.adjust_crop_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.draw_btn.setEnabled(True)
        self.draw_btn.setChecked(False)
        self.update_cropped()

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def context_menu(self, event):
        pass

    def finish(self):
        if self.rubberband is not None:
            self.view.scene().removeItem(self.rubberband)
            self.rubberband = None

        self.view.setCursor(Qt.ArrowCursor)
        self.widget.remove_app_widget()
        self.helper.deleteLater()

    def undo(self, kind, info):
        index, rect, ratio = info
        print(info, "undo cropbox")
        self.renderer.set_cropbox(index, rect, True)

    def redo(self, kind, info):
        self.undo(kind, info)
