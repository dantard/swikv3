import os
import time
import swik.resources

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QIcon
from PyQt5.QtWidgets import QApplication, QFileDialog, QDialog, QMessageBox, QHBoxLayout, \
    QWidget, QTabWidget, QVBoxLayout, QToolBar, \
    QSplitter, QGraphicsScene, QProgressBar, QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, QFrame, QSizePolicy
from pymupdf import Document

from swik.layout_manager import LayoutManager
from swik.swik_graphview import SwikGraphView
from swik.dialogs import PasswordDialog
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
        self.renderer.file_changed.connect(self.file_modified)

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
        self.tool_form_btn = self.mode_group.add(tool_form, icon=":/icons/form.png", text="Mimic PDF")
        self.mode_group.add(tool_nume, icon=":/icons/number.png", text="Number pages")

        # self.mode_group.append(self.toolbar)

        self.manager.tool_done.connect(self.tool_done)

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

        self.outline = QTreeWidget()
        self.outline.setHeaderHidden(True)
        self.outline.itemSelectionChanged.connect(self.toc_selected)

        tab = QTabWidget()
        tab.addTab(self.miniature_view, "Miniature")
        tab.addTab(self.outline, "ToC")
        tab.setMaximumWidth(self.miniature_view.maximumWidth())
        self.splitter.addWidget(tab)
        self.splitter.addWidget(helper)
        self.set_interactable(False)
        self.preferences_changed()
        QApplication.processEvents()

    def reload_file(self):
        self.file_changed_frame.setVisible(False)
        self.open_file(self.renderer.get_filename())

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
        print(s[1].rotation, s[1].rotation_matrix, "lalala")
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

    def set_protected_interaction(self, status):
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
        self.update_toc()

        pdf_widgets = [item for item in self.view.scene().items() if isinstance(item, PdfWidget)]
        if len(pdf_widgets) > 0:
            self.tool_form_btn.click()

    class TocWidgetItem(QTreeWidgetItem):
        def __init__(self, item):
            super().__init__([item.title, str(item.page)])
            self.item = item

    def update_toc(self):
        self.outline.clear()
        items = self.renderer.get_toc()
        parents = {}
        for item in items:
            twi = self.TocWidgetItem(item)
            if item.level == 1:
                self.outline.addTopLevelItem(twi)
                parents[2] = twi
            else:
                parents[item.level].addChild(twi)
                parents[item.level + 1] = twi

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
                self.tabw.tab_close_requested.emit(self)

    def save_file(self, name=None):
        name = self.renderer.get_filename() if name is None else name
        if self.renderer.get_num_of_pages() > 100:
            self.progressing = Progressing(self, title="Saving PDF...")
            self.progressing.start(self.renderer.save_pdf, name, callback=self.saved)
        else:
            result = self.renderer.save_pdf(name, False)
            self.saved(result, name)

        self.file_changed.emit()
        self.update_tab_text()

    def apply_post_save_artifacts(self, filename):
        # Signature
        signature = next((sig for sig in self.view.items() if isinstance(sig, SignerRectItem)), None)
        if signature is not None:
            output_filename = ToolSign.sign_document(signature, filename)
            if output_filename:
                self.open_requested.emit(output_filename, self.view.page, self.view.get_ratio())

        # self.manager.clear()

    def saved(self, ret_code, name):
        print("Saved file, applying post save artifacts", name)
        self.apply_post_save_artifacts(name)

    def save_file_as(self):
        name = self.renderer.get_filename()
        name, _ = QFileDialog.getSaveFileName(self, "Save PDF Document", name, "PDF Files (*.pdf)")
        if name:
            return self.save_file(name)
        return False

    def rename(self):
        filename = self.renderer.get_filename()
        self.save_file_as()
        os.remove(filename)

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
