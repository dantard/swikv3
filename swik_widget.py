import os
import subprocess
import sys
import time

from PyQt5.QtNetwork import QUdpSocket, QHostAddress

import resources
import pyclip
from PyQt5 import QtGui
from PyQt5.QtCore import QPointF, Qt, QTimer, pyqtSignal, QRectF, QEvent
from PyQt5.QtGui import QPainter, QIcon, QKeySequence, QKeyEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut, QFileDialog, QDialog, QMessageBox, QHBoxLayout, \
    QWidget, QTabWidget, QVBoxLayout, QToolBar, \
    QPushButton, QSizePolicy, QTabBar, QProgressDialog, QSplitter, QGraphicsScene, QLabel, QProgressBar

import utils
from GraphView import GraphView
from LayoutManager import LayoutManager
from SwikGraphView import SwikGraphView
from changestracker import ChangesTracker
from dialogs import PasswordDialog
from font_manager import FontManager
from groupbox import GroupBox
from keyboard_manager import KeyboardManager
from long_press_button import LongPressButton
from manager import Manager
from miniature_view import MiniatureView
from progressing import Progressing
from scene import Scene
from toolbars.zoom_toolbar import ZoomToolbar
from tools.replace_fonts.tool_replace_fonts import ToolReplaceFonts
from tools.tool_insert_image import ToolInsertImage, ToolInsertSignatureImage
from tools.tool_mimic_pdf import ToolMimicPDF
from tools.tool_numerate import ToolNumerate
from tools.toolcrop import ToolCrop
from tools.toolrearranger import ToolRearrange
from tools.toolredactannotation import ToolRedactAnnotation
from tools.toolsign import ToolSign
from tools.toolsquareannotation import ToolSquareAnnotation
from tools.tooltextselection import ToolTextSelection
from toolbars.navigationtoolbar import NavigationToolbar
from page import Page
from renderer import MuPDFRenderer
from toolbars.searchtoolbar import TextSearchToolbar
from widgets.pdf_widget import PdfCheckboxWidget


class Splitter(QSplitter):

    def __init__(self, a):
        super().__init__(a)

    def moveEvent(self, a0: QtGui.QMoveEvent) -> None:
        super().moveEvent(a0)
        # print("moveevent", a0)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(a0)
        # print("Moveevntnt")

    def releaseMouse(self) -> None:
        super().releaseMouse()
        # print("splitter released")


class SwikWidget(QWidget):
    interaction_changed = pyqtSignal(QWidget)
    open_requested = pyqtSignal(str, int, float)
    file_changed = pyqtSignal()
    progress = pyqtSignal(float)

    def __init__(self, window, tab_widget, config):
        super().__init__()
        self.interaction_enabled = False
        self.win = window
        self.tabw = tab_widget
        self.config = config
        self.renderer = MuPDFRenderer()
        self.renderer.document_changed.connect(self.document_changed)

        self.scene = Scene()
        self.manager = Manager(self.renderer, self.config)
        self.view = SwikGraphView(self.manager, self.renderer, self.scene, page=Page,
                                  mode=self.config.private.get('mode', default=LayoutManager.MODE_VERTICAL))
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.TextAntialiasing)
        self.view.set_natural_hscroll(self.config.general.get('natural_hscroll'))
        self.view.drop_event.connect(self.drop_event_received)
        self.view.document_ready.connect(self.document_ready)

        self.miniature_view = MiniatureView(self.manager, self.renderer, QGraphicsScene())
        self.miniature_view.setRenderHint(QPainter.Antialiasing)
        self.miniature_view.setRenderHint(QPainter.TextAntialiasing)
        self.miniature_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.miniature_view.setRenderHint(QPainter.HighQualityAntialiasing)
        self.miniature_view.setRenderHint(QPainter.NonCosmeticDefaultPen)
        self.miniature_view.setMaximumWidth(350)
        self.miniature_view.setMinimumWidth(180)
        # self.miniature_view.set_alignment(Qt.AlignTop)
        #        self.miniature_view.set_fit_width(True)
        self.view.page_clicked.connect(self.miniature_view.set_page)
        self.miniature_view.page_clicked.connect(self.view.set_page)
        self.manager.set_view(self.view)
        self.font_manager = FontManager(self.renderer)

        self.vlayout, self.hlayout, self.ilayout, self.app_layout = QVBoxLayout(), QHBoxLayout(), QHBoxLayout(), QVBoxLayout()
        self.vlayout.addLayout(self.hlayout)
        self.hlayout.addLayout(self.ilayout)

        helper, self.app_helper = QWidget(), QWidget()
        helper.setLayout(self.vlayout)
        self.app_helper.setLayout(self.app_layout)
        self.app_helper.setMaximumWidth(0)

        sp = QSplitter(Qt.Horizontal)
        sp.addWidget(self.app_helper)
        sp.addWidget(self.view)
        sp.setSizes([20, 100])
        self.ilayout.addWidget(sp)
        self.app_handle = sp.handle(1)
        self.app_handle.setDisabled(True)

        tool_text = self.manager.register_tool(
            ToolTextSelection(self.view, self.renderer, self.font_manager, self.config), True)
        self.tool_sign = self.manager.register_tool(ToolSign(self.view, self.renderer, self.config, widget=self))
        tool_rear = self.manager.register_tool(
            ToolRearrange(self.view, [self.miniature_view], self.renderer, self.config))
        tool_reda = self.manager.register_tool(ToolRedactAnnotation(self.view, self.renderer, self.config))
        tool_sqan = self.manager.register_tool(ToolSquareAnnotation(self.view, self.renderer, self.config))
        tool_crop = self.manager.register_tool(ToolCrop(self.view, self.renderer, self.config))
        tool_imag = self.manager.register_tool(ToolInsertImage(self.view, self.renderer, self.config))
        tool_sigi = self.manager.register_tool(ToolInsertSignatureImage(self.view, self.renderer, self.config))
        # tool_font = self.manager.register_tool(
        #    ToolReplaceFonts(self.view, self.renderer, self.config, font_manager=self.font_manager, widget=self))
        # tool_font.file_generate.connect(self.open_requested.emit)

        tool_mimi = self.manager.register_tool(
            ToolMimicPDF(self.view, self.renderer, self.config, font_manager=self.font_manager, widget=self))

        tool_nume = self.manager.register_tool(
            ToolNumerate(self.view, self.renderer, self.config, font_manager=self.font_manager))

        self.key_manager = KeyboardManager(self)

        #        self.key_manager.register_action(Qt.Key_Shift, lambda: self.manager.use_tool(tool_drag), self.manager.finished)
        self.key_manager.register_combination_action('Ctrl+R', lambda: self.open_file(self.renderer.get_filename()))
        self.key_manager.register_combination_action('Ctrl+i', self.view.toggle_page_info)
        self.key_manager.register_combination_action('Ctrl+C', lambda: self.manager.keyboard('Ctrl+C'))
        self.key_manager.register_combination_action('Ctrl+V', lambda: self.manager.keyboard('Ctrl+V'))
        self.key_manager.register_combination_action('Ctrl+A', lambda: self.manager.keyboard('Ctrl+A'))
        self.key_manager.register_combination_action('Ctrl+T',
                                                     self.manager.get_tool(ToolTextSelection).iterate_selection_mode)
        self.key_manager.register_combination_action('Ctrl+M', self.iterate_mode)
        self.key_manager.register_combination_action('Ctrl+Z', self.scene.tracker().undo)
        self.key_manager.register_combination_action('Ctrl+Shift+Z', self.scene.tracker().redo)
        self.key_manager.register_combination_action('Ctrl+B', self.iterate_bar_position)

        self.toolbar = QToolBar()
        self.toolbar.addAction("Open", self.open_button).setIcon(QIcon(":/icons/open.png"))
        self.save_btn = self.toolbar.addAction("Save", self.save_file)
        self.save_btn.setIcon(QIcon(":/icons/save.png"))
        # self.toolbar.addSeparator()
        # self.toolbar.addWidget(LongPressButton())

        self.mode_group = GroupBox(self.manager.use_tool)
        self.mode_group.add(tool_text, icon=":/icons/text_cursor.png", text="Select Text", default=True)
        self.sign_btn = self.mode_group.add(self.tool_sign, icon=":/icons/sign.png", text="Sign")
        self.mode_group.add(tool_crop, icon=":/icons/crop.png", text="Crop")
        self.mode_group.add(tool_sqan, icon=":/icons/annotate.png", text="Annotate")
        self.mode_group.add(tool_reda, icon=":/icons/white.png", text="Anonymize")
        self.mode_group.add(tool_imag, icon=":/icons/image.png", text="Insert Image")
        self.image_sign_btn = self.mode_group.add(tool_sigi, icon=":/icons/signature.png", text="Insert Signature",
                                                  separator=True)
        self.mode_group.add(tool_rear, icon=":/icons/shuffle.png", text="Shuffle Pages")
        #        self.mode_group.add(tool_font, icon=":/icons/replace_fonts.png", text="Replace Fonts")
        self.mode_group.add(tool_mimi, icon=":/icons/mimic.png", text="Mimic PDF")
        self.mode_group.add(tool_nume, icon=":/icons/numerate.png", text="Replace Fonts")
        # self.mode_group.append(self.toolbar)

        self.manager.tool_finished.connect(self.tool_finished)

        self.zoom_toolbar = ZoomToolbar(self.view, self.toolbar)
        self.nav_toolbar = NavigationToolbar(self.view, self.toolbar)
        self.finder_toolbar = TextSearchToolbar(self.view, self.renderer, self.toolbar)
        self.load_progress = QProgressBar()
        self.load_progress.setMaximumWidth(250)
        self.load_progress.setFormat("Loading...")
        self.load_progress_action = self.toolbar.addWidget(self.load_progress)
        self.load_progress_action.setVisible(False)

        self.splitter = Splitter(Qt.Horizontal)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.splitter)

        # Lateral Bar
        self.lateral_bar = QToolBar()
        self.lateral_bar.addSeparator()
        self.mode_group.append(self.lateral_bar)

        for w in [self.vlayout, self.hlayout, self.ilayout, self.app_layout, self.splitter, helper, self.lateral_bar]:
            w.setContentsMargins(0, 0, 0, 0)

        self.splitter.addWidget(self.miniature_view)
        self.splitter.addWidget(helper)
        self.set_interactable(False)
        self.preferences_changed()
        QApplication.processEvents()

    def set_app_widget(self, widget, max_width=500):
        self.app_helper.setMaximumWidth(max_width)
        self.app_layout.addWidget(widget)
        self.app_handle.setDisabled(False)

    def remove_app_widget(self, widget):
        self.app_layout.removeWidget(widget)
        self.app_helper.setMaximumWidth(0)
        self.app_handle.setDisabled(True)

    def tool_finished(self, action, data):
        if action == Manager.OPEN_REQUESTED:
            self.open_file(data)
            self.manager.use_tool(self.tool_sign)
        else:
            self.mode_group.reset()

    def set_ratio(self, ratio):
        print("set_ratio_widget", ratio)
        self.view.set_ratio(ratio, True)

    def set_page(self, page):
        self.view.set_page(page)

    def set_mode(self, mode):
        self.view.layout_manager.set_mode(mode, False)

    def document_ready(self):
        pass

    def drop_event_received(self, vector):
        for file in vector:
            self.open_requested.emit(file, 0, self.view.get_ratio())

    def set_interactable(self, enable):
        self.mode_group.set_enabled(enable)
        self.zoom_toolbar.setEnabled(enable)
        self.nav_toolbar.setEnabled(enable)
        self.finder_toolbar.setEnabled(enable)
        self.save_btn.setEnabled(enable)
        self.interaction_enabled = enable
        self.interaction_changed.emit(self)

    def is_interaction_enabled(self):
        return self.interaction_enabled

    def preferences_changed(self):
        self.sign_btn.setEnabled(self.manager.get_tool(ToolSign).usable())
        self.image_sign_btn.setEnabled(self.manager.get_tool(ToolInsertSignatureImage).usable())
        self.update_lateral_bar_position()

    def iterate_bar_position(self):
        pos = self.config.general.get('lateral_bar_position', default=0)
        pos = (pos + 1) % 4
        self.config.general.set('lateral_bar_position', pos)
        self.update_lateral_bar_position()

    def update_lateral_bar_position(self):
        pos = self.config.general.get('lateral_bar_position', default=0)
        if pos == 0:
            self.lateral_bar.setOrientation(Qt.Vertical)
            self.hlayout.insertWidget(0, self.lateral_bar)
        elif pos == 1:
            self.lateral_bar.setOrientation(Qt.Vertical)
            self.hlayout.insertWidget(self.hlayout.count(), self.lateral_bar)
        elif pos == 2:
            self.lateral_bar.setOrientation(Qt.Horizontal)
            self.vlayout.insertWidget(0, self.lateral_bar)
        else:
            self.lateral_bar.setOrientation(Qt.Horizontal)
            self.vlayout.insertWidget(self.vlayout.count(), self.lateral_bar)

    #

    # self.sign_btn.setEnabled(self.config.get("p12") is not None)
    # self.image_sign_btn.setEnabled(self.config.get("image_signature") is not None)

    def set_tab(self, tab):
        self.tab = tab

    def statusBar(self):
        return self.win.statusBar()

    def should_open_here(self, filename):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText("Open file {} in this window?".format(os.path.basename(filename)))
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        lay: QHBoxLayout = msg_box.findChild(QHBoxLayout)
        w = lay.takeAt(3)
        lay.insertWidget(1, w.widget())
        w = lay.takeAt(2)
        lay.insertWidget(3, w.widget())
        user_choice = msg_box.exec()
        if user_choice == QMessageBox.Yes:
            return True
        elif user_choice == QMessageBox.No:
            return False
        else:
            return True

    def iterate_mode(self):
        mode = (self.view.get_mode() + 1) % len(LayoutManager.modes)
        self.view.set_mode(mode)
        self.statusBar().showMessage("Mode " + LayoutManager.modes[mode], 2000)

    def flatten(self, open=True):
        filename = self.renderer.get_filename().replace(".pdf", "-flat.pdf")

        res = self.renderer.flatten(filename)

        if res == MuPDFRenderer.FLATTEN_ERROR:
            QMessageBox.critical(self, "Flatten", "Error while flattening the document", QMessageBox.Ok)
            return

        else:
            if res == MuPDFRenderer.FLATTEN_WORKAROUND:
                QMessageBox.warning(self, "Flatten",
                                    "Original PDF has problems, a workaround has been applied. Check result correctness.",
                                    QMessageBox.Ok)

            if open:
                self.open_requested.emit(filename, self.view.page, self.view.ratio)

    def extract_fonts(self):
        fonts = self.renderer.save_fonts(".")
        QMessageBox.information(self, "Fonts extracted", "Extracted " + str(len(fonts)) + "fonts")

    def undo(self):
        selected = self.view.scene().selectedItems()
        for item in selected:
            item.deserialize(self.info)

    def copy(self):
        pass

    def document_changed(self):
        # Clear views and fonts
        self.manager.clear()
        self.view.clear()
        self.miniature_view.clear()
        self.font_manager.clear_document_fonts()

        self.load_progress_action.setVisible(True)
        self.load_progress.setMaximum(self.renderer.get_num_of_pages())

        # Create pages
        self.view.layout_manager.reset()
        self.miniature_view.layout_manager.reset()

        for i in range(self.renderer.get_num_of_pages()):
            # Create Page
            page = self.view.create_page(i, self.view.get_ratio())
            self.view.layout_manager.update_layout(page)

            # Create Miniature Page
            mini_page = self.miniature_view.create_page(i)
            self.miniature_view.layout_manager.update_layout(mini_page)

            # Update progress bar
            self.load_progress.setValue(i + 1)

        self.load_progress_action.setVisible(False)
        self.update_tab_text()

    def update_tab_text(self):
        # Update the tab name
        my_index = self.tabw.indexOf(self)
        text = os.path.basename(self.renderer.get_filename())
        font_metrics = self.tabw.fontMetrics()
        text = font_metrics.elidedText(text, Qt.ElideRight, 200)
        self.tabw.setTabText(my_index, text)
        self.tabw.setTabToolTip(my_index, self.renderer.get_filename())
        self.mode_group.reset()

    def get_filename(self):
        return self.renderer.get_filename()

    def manage_tool(self, tool):
        self.manager.use_tool(tool)

    def open_button(self):
        # self.set_ratio(1)
        self.open_file()

    def open_file(self, filename=None):
        if filename is None:
            last_dir_for_open = self.config.private.get('last_dir_for_open')
            filename, _ = QFileDialog.getOpenFileName(self, 'Open file', last_dir_for_open, 'PDF (*.pdf)')

        if filename:
            self.mode_group.reset()
            res = self.renderer.open_pdf(filename)
            if res == MuPDFRenderer.OPEN_REQUIRES_PASSWORD:
                dialog = PasswordDialog(False, parent=self)
                if dialog.exec() == QDialog.Accepted:
                    res = self.renderer.open_pdf(filename, dialog.getText())

            if res == MuPDFRenderer.OPEN_OK:
                self.set_interactable(True)
                self.file_changed.emit()
                # To update the number of page
                self.view.page_scrolled()
                self.config.update_recent(self.renderer.get_filename())
                self.config.flush()

            else:
                QMessageBox.warning(self, "Error", "Error opening file")

    def save_file(self, name=None):
        name = self.renderer.get_filename() if name is None else name
        if self.renderer.get_num_of_pages() > 50:
            self.progressing = Progressing(self, title="Saving PDF...")
            self.progressing.start(self.renderer.save_pdf, name, callback=self.saved)
        else:
            self.manager.clear()
            self.saved(self.renderer.save_pdf(name))

    def saved(self, ret_code):
        print("Error saving file", ret_code)

    def save_file_as(self):
        name = self.renderer.get_filename()
        name, _ = QFileDialog.getSaveFileName(self, "Save PDF Document", name, "PDF Files (*.pdf)")
        if name:
            return self.save_file(name)
        return False

    def open_with_other(self, command):
        if command is not None:
            os.system(command + " '" + self.renderer.get_filename() + "' &")
        else:
            self.config.edit()

    # TODO::::CONVERT
    def append_pdf(self, filename):
        pd = Progressing(self, 100)

        def append():
            index = self.renderer.get_num_of_pages()
            num_of_pages_added = self.renderer.append_pdf(filename)

            for i in range(num_of_pages_added):
                self.view.create_page(index + i, self.view.get_ratio())
                self.miniature_view.create_page(index + i)

                time.sleep(0.01)
                pd.set_progress(i * 100 / num_of_pages_added)

            pd.set_progress(100)
            self.view.update_layout()
            self.miniature_view.update_layout()

        pd.start(append)

    def deleteLater(self):
        self.finder_toolbar.close()
        super().deleteLater()
