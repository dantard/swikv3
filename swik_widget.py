import os
import subprocess
import sys

from PyQt5.QtNetwork import QUdpSocket, QHostAddress

import resources
import pyclip
from PyQt5 import QtGui
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QPainter, QIcon, QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut, QFileDialog, QDialog, QMessageBox, QHBoxLayout, QWidget, QTabWidget, QVBoxLayout, QToolBar, \
    QPushButton, QSizePolicy, QTabBar

import utils
from GraphView import GraphView
from LayoutManager import LayoutManager
from SwikGraphView import SwikGraphView
from changestracker import ChangesTracker
from dialogs import PasswordDialog
from font_manager import FontManager
from groupbox import GroupBox
from keyboard_manager import KeyboardManager
from manager import Manager
from scene import Scene
from toolbars.zoom_toolbar import ZoomToolbar
from tools.tool_drag import ToolDrag
from tools.toolcrop import ToolCrop
from tools.toolrearranger import ToolRearrange
from tools.toolredactannotation import ToolRedactAnnotation
from tools.toolsign import ToolSign
from tools.toolsquareannotation import ToolSquareAnnotation
from tools.tooltextselection import TextSelection
from toolbars.navigationtoolbar import NavigationToolbar
from page import Page
from renderer import MuPDFRenderer
from toolbars.searchtoolbar import TextSearchToolbar


class SwikWidget(QWidget):

    def __init__(self, window, tab_widget, config):
        super().__init__()
        self.win = window
        self.tabw = tab_widget
        self.config = config
        self.renderer = MuPDFRenderer()
        self.renderer.document_changed.connect(self.document_changed)

        self.scene = Scene()
        self.manager = Manager(self.renderer, self.config)
        self.view = SwikGraphView(self.manager, self.renderer, self.scene, page=Page, mode=self.config.get('mode', LayoutManager.MODE_VERTICAL))
        self.manager.set_view(self.view)

        self.font_manager = FontManager(self.renderer)
        self.font_manager.update_system_fonts()
        self.font_manager.update_swik_fonts()

        self.manager.register_tool('text_selection', TextSelection(self.view, self.renderer, self.font_manager, self.config), True)
        self.manager.register_tool('sign', ToolSign(self.view, self.renderer, self.config), False)
        self.manager.register_tool('rearrange', ToolRearrange(self.view, self.renderer, self.config), False)
        self.manager.register_tool('redact_annot', ToolRedactAnnotation(self.view, self.renderer, self.config), False)
        self.manager.register_tool('square_annot', ToolSquareAnnotation(self.view, self.renderer, self.config), False)
        self.manager.register_tool('crop', ToolCrop(self.view, self.renderer, self.config), False)
        self.manager.register_tool('drag', ToolDrag(self.view, self.renderer, self.config), False)

        self.key_manager = KeyboardManager(self)
        self.key_manager.register_action(Qt.Key_Delete, self.delete_objects)
        self.key_manager.register_action(Qt.Key_Shift, lambda: self.manager.use_tool("drag"), self.manager.finished)
        self.key_manager.register_combination_action('Ctrl+C', lambda: self.manager.keyboard('Ctrl+C'))
        self.key_manager.register_combination_action('Ctrl+V', lambda: self.manager.keyboard('Ctrl+V'))
        self.key_manager.register_combination_action('Ctrl+A', lambda: self.manager.keyboard('Ctrl+A'))
        self.key_manager.register_combination_action('Ctrl+T', self.manager.get_tool("text_selection").iterate_selection_mode)
        self.key_manager.register_combination_action('Ctrl+M', self.iterate_mode)
        self.key_manager.register_combination_action('Ctrl+Z', self.scene.tracker().undo)
        self.key_manager.register_combination_action('Ctrl+Shift+Z', self.scene.tracker().redo)

        self.config.load("swik.yaml")

        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.TextAntialiasing)
        self.view.set_natural_hscroll(self.config.get('natural_hscroll'))

        self.toolbar = QToolBar()
        self.toolbar.addAction("Open", self.open_file).setIcon(QIcon(":/icons/open.png"))
        self.toolbar.addAction("Save", self.save_file).setIcon(QIcon(":/icons/save.png"))
        self.toolbar.addSeparator()

        self.mode_group = GroupBox()
        self.mode_group.add(self.manage_tool, True, icon=":/icons/text_cursor.png", text="Select Text", tool="text_selection")
        self.sign_btn = self.mode_group.add(self.manage_tool, icon=":/icons/sign.png", text="Sign", tool="sign")
        self.mode_group.add(self.manage_tool, icon=":/icons/crop.png", text="Crop", tool="crop")
        self.mode_group.add(self.manage_tool, icon=":/icons/annotate.png", text="Annotate", tool="square_annot")
        self.mode_group.add(self.manage_tool, icon=":/icons/white.png", text="Anonymize", tool="redact_annot")
        self.mode_group.add(self.manage_tool, icon=":/icons/shuffle.png", text="Shuffle Pages", tool="rearrange")
        self.sign_btn.setEnabled(self.config.get("p12") is not None)

        self.mode_group.append(self.toolbar)
        self.manager.tool_finished.connect(self.mode_group.reset)
        self.zoom_toolbar = ZoomToolbar(self.view, self.toolbar)
        self.nav_toolbar = NavigationToolbar(self.view, self.toolbar)
        self.finder_toolbar = TextSearchToolbar(self.view, self.renderer, self.toolbar)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.view)

    def preferences_changed(self):
        self.sign_btn.setEnabled(self.config.get("p12") is not None)

    def set_tab(self, tab):
        self.tab = tab

    def statusBar(self):
        return self.win.statusBar()

    def delete_objects(self):
        items = self.view.scene().selectedItems()
        self.scene.tracker().items_removed(items)
        for item in items:
            self.view.scene().removeItem(item)

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
        self.renderer.flatten(filename)
        if open:
            self.open_file(filename)

    def extract_fonts(self):
        fonts = self.renderer.save_fonts(".")
        QMessageBox.information(self, "Fonts extracted", "Extracted " + str(len(fonts)) + "fonts")

    def undo(self):
        selected = self.view.scene().selectedItems()
        for item in selected:
            item.deserialize(self.info)

    def copy(self):
        selected = self.view.scene().selectedItems()
        for item in selected:
            kind = type(item)
            print("Creating ", kind, " from ", item, " with ", item.get_kwargs())
            # obj = kind(copy=item, offset=QPointF(50, 50))
            obj = kind()
            info = {}
            item.serialize(self.info)

    def document_changed(self):
        self.font_manager.update_document_fonts()
        self.tabw: QTabWidget
        my_index = self.tabw.indexOf(self)
        self.tabw.setTabText(my_index, os.path.basename(self.renderer.get_filename()))

    def get_filename(self):
        return self.renderer.get_filename()

    def manage_tool(self):
        button = self.sender()
        if button is not None:
            self.manager.use_tool(button.get_tool())

    def open_file(self, filename=None):
        if filename is None:
            last_dir_for_open = self.config.get('last_dir_for_open', None)
            filename, _ = QFileDialog.getOpenFileName(self, 'Open file', last_dir_for_open, 'PDF (*.pdf)')

        if filename:
            self.mode_group.reset()
            res = self.renderer.open_pdf(filename)
            if res == MuPDFRenderer.OPEN_REQUIRES_PASSWORD:
                dialog = PasswordDialog(False, parent=self)
                if dialog.exec() == QDialog.Accepted:
                    res = self.renderer.open_pdf(filename, dialog.getText())

            if res == MuPDFRenderer.OPEN_OK:
                self.config.set('last', self.renderer.get_filename())
                self.config.flush()
            else:
                QMessageBox.warning(self, "Error", "Error opening file")

    def save_file(self, name=None):
        name = self.renderer.get_filename() if name is None else name
        return self.renderer.save_pdf(name)

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

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(a0)
        if not self.key_manager.key_pressed(a0):
            self.manager.key_pressed(a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        super().keyReleaseEvent(a0)
        if not self.key_manager.key_released(a0):
            self.manager.key_released(a0)
