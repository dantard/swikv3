import os
import pathlib
import time
from os.path import expanduser

import pymupdf

from swik import utils

from swik.changes_tracker import ChangesTracker

import swik.resources

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QIcon
from PyQt5.QtWidgets import QApplication, QFileDialog, QDialog, QMessageBox, QHBoxLayout, \
    QWidget, QTabWidget, QVBoxLayout, QToolBar, \
    QSplitter, QGraphicsScene, QProgressBar, QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, QFrame, QSizePolicy
from pymupdf import Document

from swik.file_browser import FileBrowser
from swik.layout_manager import LayoutManager
from swik.swik_graphview import SwikGraphView
from swik.dialogs import PasswordDialog, DictDialog, TextBoxDialog
from swik.font_manager import FontManager
from swik.groupbox import GroupBox
from swik.interfaces import Shell
from swik.keyboard_manager import KeyboardManager
from swik.manager import Manager
from swik.miniature_view import MiniatureView
from swik.page import Page
from swik.progressing import Progressing
from swik.renderer import MuPDFRenderer
from swik.scene import Scene
from swik.title_widget import AppBar
from swik.toolbars.navigation_toolbar import NavigationToolbar
from swik.toolbars.search_toolbar import TextSearchToolbar
from swik.toolbars.zoom_toolbar import ZoomToolbar
from swik.tools.tool_form import ToolForm
from swik.tools.tool_insert_image import ToolInsertSignatureImage
from swik.tools.tool_mimic_pdf import ToolMimicPDF
from swik.tools.tool_numerate import ToolNumerate
from swik.tools.tool_crop import ToolCrop
from swik.tools.tool_rearranger import ToolRearrange
from swik.tools.tool_redactannotation import ToolRedactAnnotation
from swik.tools.tool_sign import ToolSign, SignerRectItem
from swik.tools.tool_squareannotation import ToolSquareAnnotation
from swik.tools.tool_textselection import ToolTextSelection
from swik.widgets.pdf_widget import PdfWidget


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


class SwikWidget(Shell):
    interaction_changed = pyqtSignal(QWidget)
    open_requested = pyqtSignal(str, int, float)
    close_requested = pyqtSignal(Shell)
    file_changed = pyqtSignal(Shell)
    dirtiness_changed = pyqtSignal(object, bool)
    progress = pyqtSignal(float)
    dying = pyqtSignal()

    def __init__(self, window, config):
        super().__init__()
        self.interaction_enabled = False
        self.win = window
        self.config = config
        self.params = []
        self.placeholder = None
        self.renderer = MuPDFRenderer()
        self.renderer.document_changed.connect(self.document_changed)
        self.renderer.file_changed.connect(self.file_modified)

        self.changes_tracker = ChangesTracker()
        self.changes_tracker.dirty.connect(self.dirtiness_has_changed)

        self.scene = Scene(self.changes_tracker)
        self.manager = Manager(self.renderer, self.config)
        self.view = SwikGraphView(self.manager, self.renderer, self.scene, page=Page,
                                  mode=self.config.private.get('mode', default=LayoutManager.MODE_VERTICAL))
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
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
        self.miniature_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.page_clicked.connect(self.miniature_view.set_page)
        self.miniature_view.page_clicked.connect(self.view.set_page)
        self.manager.set_view(self.view)
        self.font_manager = FontManager(self.renderer)

        self.vlayout, self.hlayout, self.ilayout, self.app_layout = QVBoxLayout(), QHBoxLayout(), QHBoxLayout(), QVBoxLayout()

        self.file_changed_frame = QToolBar()
        self.file_changed_frame.setContentsMargins(0, 0, 0, 0)
        self.file_changed_frame.addWidget(QLabel("File has changed on disk"))
        stretch = QWidget()
        stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.file_changed_frame.addWidget(stretch)
        file_changed_reload_btn = QPushButton("⟳")
        file_changed_reload_btn.setFixedSize(25, 25)
        file_changed_close_btn = QPushButton("✕")
        file_changed_close_btn.setFixedSize(25, 25)
        file_changed_close_btn.clicked.connect(self.file_changed_frame.hide)
        file_changed_reload_btn.clicked.connect(self.reload_file)
        self.file_changed_frame.addWidget(file_changed_reload_btn)
        self.file_changed_frame.addWidget(file_changed_close_btn)
        self.file_changed_frame.hide()

        self.vlayout.addWidget(self.file_changed_frame)
        self.vlayout.addLayout(self.hlayout)
        self.hlayout.addLayout(self.ilayout)

        helper = QWidget()
        helper.setLayout(self.vlayout)

        self.app_bar = AppBar()
        self.app_bar.close.connect(self.app_closed)

        sp = QSplitter(Qt.Horizontal)
        sp.addWidget(self.app_bar)

        sp.addWidget(self.view)
        sp.setSizes([20, 100])
        self.ilayout.addWidget(sp)
        self.app_handle = sp.handle(1)
        self.app_handle.setDisabled(True)

        tool_text = self.manager.register_tool(ToolTextSelection(self), True)
        self.tool_sign = self.manager.register_tool(ToolSign(self))
        tool_rear = self.manager.register_tool(ToolRearrange(self))
        tool_reda = self.manager.register_tool(ToolRedactAnnotation(self))
        tool_sqan = self.manager.register_tool(ToolSquareAnnotation(self))
        tool_crop = self.manager.register_tool(ToolCrop(self))
        tool_sigi = self.manager.register_tool(ToolInsertSignatureImage(self))
        tool_form = self.manager.register_tool(ToolForm(self))
        tool_mimi = self.manager.register_tool(ToolMimicPDF(self))
        tool_nume = self.manager.register_tool(ToolNumerate(self))

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
        self.mode_group.add(tool_sigi, icon=":/icons/image.png", text="Insert Image")
        self.mode_group.add(tool_rear, icon=":/icons/shuffle.png", text="Shuffle Pages")
        self.mode_group.add(tool_mimi, icon=":/icons/mimic.png", text="Mimic PDF")
        self.tool_form_btn = self.mode_group.add(tool_form, icon=":/icons/form.png", text="Forms")
        self.mode_group.add(tool_nume, icon=":/icons/number.png", text="Number pages")

        # self.mode_group.append(self.toolbar)

        self.manager.tool_done.connect(self.tool_done)

        self.zoom_toolbar = ZoomToolbar(self.view, self.toolbar)
        self.toolbar.addSeparator()
        self.toolbar.addAction("ɱ", self.iterate_mode)
        self.toolbar.addSeparator()

        self.nav_toolbar = NavigationToolbar(self.view, self.toolbar)
        self.finder_toolbar = TextSearchToolbar(self.view, self.renderer, self.toolbar)
        self.load_progress = QProgressBar()
        self.load_progress.setMaximumWidth(100)
        # self.load_progress.setFormat("Loading...")
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

        self.outline = QTreeWidget()
        self.outline.setHeaderHidden(True)
        self.outline.itemSelectionChanged.connect(self.toc_selected)

        self.file_browser = FileBrowser(expanduser("~"))
        self.file_browser.signals.file_selected.connect(self.file_selected)

        # self.rclone_browser = RCloneBrowser()

        self.tab = QTabWidget()
        self.tab.addTab(self.miniature_view, "Miniature")
        self.tab.addTab(self.outline, "ToC")
        self.tab.addTab(self.file_browser, "Files")
        self.tab.setTabVisible(1, False)
        self.tab.setMaximumWidth(self.miniature_view.maximumWidth())

        self.splitter.addWidget(self.tab)
        self.splitter.addWidget(helper)
        self.set_interactable(False)
        self.preferences_changed()
        QApplication.processEvents()

    def file_selected(self, file):
        self.push_params(self.view.layout_manager.mode, self.view.ratio, 0, self.splitter.sizes())
        self.open_file(file)

    def push_params(self, mode=0, ratio=1, scroll=0, splitter=None):
        self.params.append((mode, ratio, scroll, splitter))

    def dirtiness_has_changed(self, dirty):
        self.dirtiness_changed.emit(self, dirty)
        # self.save_btn.setEnabled(dirty)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        super(SwikWidget, self).keyPressEvent(a0)
        self.manager.key_pressed(a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        super(SwikWidget, self).keyReleaseEvent(a0)
        self.manager.key_released(a0)

    def is_dirty(self):
        return self.changes_tracker.is_dirty()

    def reload_file(self):
        self.file_changed_frame.setVisible(False)
        if os.path.isfile(self.renderer.get_filename()):
            self.open_file(self.renderer.get_filename())
        else:
            QMessageBox.critical(self, "Error", "File " + self.renderer.get_filename() + " has been deleted")
            self.close_requested.emit(self)

    def file_modified(self):
        self.file_changed_frame.setVisible(True)

    def get_renderer(self):
        return self.renderer

    def get_view(self):
        return self.view

    def get_manager(self):
        return self.manager

    def get_config(self):
        return self.config

    def get_font_manager(self):
        return self.font_manager

    def get_other_views(self):
        return [self.miniature_view]

    def toc_selected(self):
        s: Document = self.renderer.document
        selected = self.outline.selectedItems()
        if len(selected) == 0:
            return
        selected = selected[0]
        page = self.view.pages[selected.item.page]
        if self.view.layout_manager.mode == LayoutManager.MODE_SINGLE_PAGE:
            self.view.move_to_page(page.index)
        p = page.mapToScene(selected.item.to)
        self.view.centerOn(p.x(), p.y() + self.view.viewport().height() / 2)

    def app_closed(self):
        self.view.set_one_shot_immediate_resize()
        self.mode_group.reset()

    def set_app_widget(self, widget, width=500, title=""):
        self.view.set_one_shot_immediate_resize()
        self.app_bar.set_item(widget, title)
        self.app_bar.set_suggested_width(width)
        self.app_handle.setDisabled(False)

    def remove_app_widget(self):
        self.view.set_one_shot_immediate_resize()
        self.app_bar.remove_item()
        self.app_bar.setMaximumWidth(0)
        self.app_handle.setDisabled(True)

    def tool_done(self, action, data):
        if action == Manager.OPEN_REQUESTED:
            self.open_file(data)
            self.manager.use_tool(self.tool_sign)
        else:
            self.mode_group.reset()

    def set_ratio(self, ratio):
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

    def set_protected_interaction(self, status):
        self.interaction_enabled = status
        self.save_btn.setEnabled(status)
        self.interaction_changed.emit(self)

    def is_interaction_enabled(self):
        return self.interaction_enabled

    def preferences_changed(self):
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

    def statusBar(self):
        return self.win.statusBar()

    def iterate_mode(self):
        mode = (self.view.get_mode() + 1) % (len(LayoutManager.modes) - 1)
        self.view.set_mode(mode, True)
        self.statusBar().showMessage("Mode " + LayoutManager.modes[mode], 2000)

    def flatten(self, open=True):
        filename = self.renderer.get_filename().replace(".pdf", "-flat.pdf")

        res = self.renderer.flatten(filename)

        if open:
            self.open_requested.emit(filename, self.view.page, self.view.ratio)

    def extract_fonts(self):
        fonts = self.renderer.save_fonts(".")
        QMessageBox.information(self, "Fonts extracted", "Extracted " + str(len(fonts)) + "fonts")

    def document_changed(self):

        # Clear views and fonts
        self.changes_tracker.clear()
        self.manager.clear()
        self.view.clear()
        self.miniature_view.clear()
        self.font_manager.clear_document_fonts()

        if len(self.params) > 0:
            mode, ratio, scroll, splitter = self.params.pop()
        else:
            scroll = 0
            ratio = self.config.get_default_ratio()
            mode = self.config.get_default_mode()
            splitter = [self.config.get_default_bar_width(), self.width() - self.config.get_default_bar_width()]

        self.splitter.setSizes(splitter)

        # Force splitter adjustment
        QApplication.processEvents()

        if ratio > 0:
            self.view.ratio = ratio
        else:
            # Precompute ratio for
            # fit width to avoid flickering
            self.view.ratio = (self.view.viewport().width() - 20) / self.renderer.get_page_width(0)
            mode = LayoutManager.MODE_FIT_WIDTH

        self.view.set_mode(mode)

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
            mini_page = self.miniature_view.create_page(i, 1)
            self.miniature_view.layout_manager.update_layout(mini_page)

            # Update progress bar
            self.load_progress.setValue(i + 1)

            # Process events every 20 pages
            # to avoid freezing the interface
            if i % 20 == 0:
                QApplication.processEvents()

        self.load_progress_action.setVisible(False)
        self.mode_group.reset()
        self.update_toc()

        pdf_widgets = [item for item in self.view.scene().items() if isinstance(item, PdfWidget)]

        if len(pdf_widgets) > 0:
            self.tool_form_btn.click()

        # Important otherwise the
        # view is not ready to be used
        QApplication.processEvents()

        if mode != LayoutManager.MODE_SINGLE_PAGE:
            self.view.set_scroll_value(scroll)
        else:
            self.view.move_to_page(scroll)

    class TocWidgetItem(QTreeWidgetItem):
        def __init__(self, item):
            super().__init__([item.title, str(item.page)])
            self.item = item

    def update_toc(self):
        self.outline.clear()
        items = self.renderer.get_toc()
        self.tab.setTabVisible(1, len(items) > 0)

        parents = {}
        for item in items:
            twi = self.TocWidgetItem(item)
            if item.level == 1:
                self.outline.addTopLevelItem(twi)
                parents[2] = twi
            else:
                parents[item.level].addChild(twi)
                parents[item.level + 1] = twi

    def get_filename(self):
        return self.renderer.get_filename()

    def open_button(self):
        self.push_params(self.view.layout_manager.mode, self.view.ratio, 0, self.splitter.sizes())
        self.open_file()

    def open_file(self, filename=None, warn=True):
        if filename is None:
            last_dir_for_open = self.config.private.get('last_dir_for_open')
            filename, ext = QFileDialog.getOpenFileName(self, 'Open file', last_dir_for_open, 'PDF (*.pdf)')

        if filename:
            _, ext = os.path.splitext(filename)

            if ext in ['.doc', '.docx', '.odt', '.rtf', '.html',
                       '.htm', '.xml', '.pptx', '.ppt', '.xls', '.xlsx']:
                result = utils.word_to_pdf(filename)
                if result == 0:
                    pass
                elif result == -4:
                    warn and QMessageBox.warning(self, "Error", "Libreoffice does not seem to be installed.")
                    self.close_requested.emit(self)
                    return
                elif result == -1:
                    warn and QMessageBox.warning(self, "Error", "Libreoffice Writer does not seem to be installed.")
                    self.close_requested.emit(self)
                    return
                elif result == -2:
                    warn and QMessageBox.warning(self, "Error", "Libreoffice Draw does not seem to be installed.")
                    self.close_requested.emit(self)
                    return
                elif result == -3:
                    warn and QMessageBox.warning(self, "Error", "Libreoffice Calc does not seem to be installed.")
                    self.close_requested.emit(self)
                    return
                else:
                    warn and QMessageBox.warning(self, "Error", "Error converting file")
                    self.close_requested.emit(self)
                    return
                filename = filename.replace(ext, '.pdf')

            elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.pnm',
                         '.pgm', '.ppm', '.xps', '.svg', '.epub', '.mobi', '.txt']:
                try:
                    file = pymupdf.open(filename)
                    pdf_bytes = file.convert_to_pdf()
                    pdf = pymupdf.open("pdf", pdf_bytes)
                    filename = filename.replace(ext, '.pdf')
                    pdf.save(filename)
                except:
                    warn and QMessageBox.warning(self, "Error", "Error converting file")
                    self.close_requested.emit(self)
                    return

            if not os.path.exists(filename):
                warn and QMessageBox.warning(self, "Error", "File does not exist")
                self.close_requested.emit(self)
                return

            self.mode_group.reset()
            res = self.renderer.open_pdf(filename)
            if res == MuPDFRenderer.OPEN_REQUIRES_PASSWORD:
                dialog = PasswordDialog(False, parent=self)
                if dialog.exec() == QDialog.Accepted:
                    res = self.renderer.open_pdf(filename, dialog.getText())

            if res == MuPDFRenderer.OPEN_OK:
                self.set_interactable(True)
                self.file_changed.emit(self)
                # To update the number of page
                self.view.page_scrolled()
                self.config.update_recent(self.renderer.get_filename())
                self.config.flush()
                self.file_browser.select(self.renderer.get_filename(), False)

            else:
                warn and QMessageBox.warning(self, "Error", "Error opening file")
                self.close_requested.emit(self)

    def save_file(self, name=None):
        name = self.renderer.get_filename() if name is None else name
        print("in save_file: ", name)

        if self.renderer.get_num_of_pages() > 100:
            self.placeholder = Progressing(self, title="Saving PDF...")
            self.placeholder.show()
            result = self.renderer.save_pdf(name, False)
            self.placeholder.close()
        else:
            result = self.renderer.save_pdf(name, False)
        if result:
            self.file_browser.select(self.renderer.get_filename(), False)
            self.file_changed.emit(self)
            self.changes_tracker.clear()
            self.mode_group.reset()

        return result

    def apply_post_save_artifacts(self, filename):
        # Signature
        signature = next((sig for sig in self.view.items() if isinstance(sig, SignerRectItem)), None)
        if signature is not None:
            output_filename = ToolSign.sign_document(signature, filename)
            if output_filename:
                self.open_requested.emit(output_filename, self.view.page, self.view.get_ratio())

        # self.manager.clear()

    def saved(self, ret_code, name):
        self.apply_post_save_artifacts(name)

    def save_file_as(self):
        name = self.renderer.get_filename()
        name, _ = QFileDialog.getSaveFileName(self, "Save PDF Document", name, "PDF Files (*.pdf)")
        print("name chosen", name)
        if name:
            return self.save_file(name)
        return False

    def rename(self):
        current_name = self.renderer.get_filename()
        name, _ = QFileDialog.getSaveFileName(self, "Save PDF Document", current_name, "PDF Files (*.pdf)")
        print("name chosen", name)
        if name:
            if self.save_file(name):
                pathlib.Path.unlink(pathlib.Path(current_name))
        return False

    def open_with_other(self, command):
        if command is not None:
            os.system(command + " '" + self.renderer.get_filename() + "' &")
        else:
            self.config.edit()

    # TODO::::CONVERT
    def append_pdf(self, filename, append_id):
        pd = Progressing(self, 100, "Appending PDF...")

        def append():
            index = self.renderer.get_num_of_pages()
            num_of_pages_added = self.renderer.append_pdf(filename)

            for i in range(num_of_pages_added):
                page = self.view.create_page(index + i, self.view.get_ratio())
                page.update_original_info({"page": i, "append_id": append_id})
                self.view.layout_manager.update_layout(page)

                page = self.miniature_view.create_page(index + i, self.miniature_view.get_ratio())
                self.miniature_view.layout_manager.update_layout(page)

                pd.set_progress(i * 100 / num_of_pages_added)

            pd.set_progress(100)
            self.view.update_layout()
            self.miniature_view.update_layout()

        pd.start(append)

    def deleteLater(self):
        self.finder_toolbar.close()
        super().deleteLater()

    def edit_metadata(self):
        dialog = DictDialog(self.renderer.get_metadata(), ["format", "encryption"], parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.renderer.set_metadata(dialog.get_dict())

    def edit_xml_metadata(self):
        dialog = TextBoxDialog(self.renderer.get_xml_metadata(), parent=self, title="Edit XML Metadata")
        if dialog.exec() == QDialog.Accepted:
            self.renderer.set_xml_metadata(dialog.get_text())

    def set_tool(self, tool):
        if tool == "shuffle":
            self.mode_group.select("Shuffle Pages")
        elif tool == "sign":
            self.mode_group.select("Sign")
        elif tool == "crop":
            self.mode_group.select("Crop")

    def die(self):
        self.finder_toolbar.die()
        self.dying.emit()
