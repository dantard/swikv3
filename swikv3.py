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
from swikconfig import SwikConfig


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.config = SwikConfig()

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('Open', self.open_file)
        open_recent = file_menu.addMenu("Open Recent")
        open_recent.aboutToShow.connect(lambda: self.config.fill_recent(self, open_recent))
        file_menu.addAction('Save', self.save_file)
        file_menu.addAction('Save as', self.save_file_as)
        #        file_menu.addAction('Locate in folder', lambda: os.system(self.config.get("file_browser") + " '" + self.renderer.get_filename() + "' &"))
        file_menu.addAction('Copy path', lambda: pyclip.copy(self.renderer.filename))
        edit_menu = menu_bar.addMenu('Edit')
        edit_menu.addSeparator()
        edit_menu.addAction('Preferences', self.preferences)

        tool_menu = menu_bar.addMenu('Tools')
        tool_menu.addAction('Flatten', lambda: self.flatten(False))
        tool_menu.addAction('Flatten and Open', lambda: self.flatten(True))
        tool_menu.addSeparator()
        tool_menu.addAction('Extract Fonts', self.extract_fonts)

        command = self.config.get("other_pdf")
        if command is not None and command != "None":
            open_wo_odf = file_menu.addMenu('Open with other Viewer')
            for line in command.split("&&"):
                data = line.split(" ")
                if len(data) == 2:
                    name, cmd = data
                else:
                    name = cmd = data[0]
                open_wo_odf.addAction(name, lambda x=cmd: self.open_with_other(x))

        self.setWindowTitle("Swik")
        self.setGeometry(100, 100, 640, 480)
        self.setAcceptDrops(True)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(QWidget(), "+")
        self.tab_widget.currentChanged.connect(self.tab_changed)

        self.setCentralWidget(self.tab_widget)

        # Open last files if required
        if self.config.get("open_last"):
            tabs = self.config.get_tabs()
            if len(tabs) == 0:
                self.create_tab()
            else:
                for tab in tabs:
                    self.create_tab(tab)

    def open_file(self, filename=None):
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")

        if filename:
            for widget in self.get_widgets():
                if widget.get_filename() is None:
                    widget.open_file(filename)
                    break
            else:
                self.create_tab(filename)

    def save_file(self):
        self.current().save_file()

    def save_file_as(self):
        self.current().save_file_as()

    def flatten(self, open):
        self.current().flatten(open)

    def extract_fonts(self):
        self.current().extract_fonts()

    def preferences(self):
        self.config.exec()
        self.config.flush()
        for widget in self.get_widgets():
            widget.preferences_changed()

    def open_with_other(self, command):
        self.current().open_with_other(command)

    def get_widgets(self):
        return [self.tab_widget.widget(i) for i in range(self.tab_widget.count() - 1)]

    def current(self):
        return self.tab_widget.currentWidget()

    def tab_changed(self, index):
        if index == self.tab_widget.count() - 1:
            self.create_tab(None)
            self.tab_widget.setCurrentIndex(index)

    def create_tab(self, filename=None):
        widget = SwikWidget(self, self.tab_widget, self.config)
        index = self.tab_widget.insertTab(self.tab_widget.count() - 1, widget, filename if filename is not None else "(None)")
        close_button = QPushButton("x")
        close_button.setContentsMargins(0, 0, 0, 15)
        close_button.setFixedSize(20, 20)
        close_button.setFlat(True)
        close_button.widget = widget
        close_button.clicked.connect(lambda y, x=widget: self.close_tab(x))
        self.tab_widget.tabBar().setTabButton(index, QTabBar.RightSide, close_button)
        if filename is not None:
            widget.open_file(filename)
        self.tab_widget.setCurrentIndex(index)
        return widget

    def close_tab(self, tab):
        print("tab", tab, "closed")
        if self.tab_widget.count() > 2:
            index = self.tab_widget.indexOf(tab)
            self.tab_widget.setCurrentIndex(index - 1)
            self.tab_widget.removeTab(index)

        filename = self.tab_widget.currentWidget().get_filename()
        self.setWindowTitle("Swik" + (" - " + filename) if filename is not None else "")

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        tabs = []
        for index in range(self.tab_widget.count() - 1):
            swik_widget = self.tab_widget.widget(index)
            tabs.append(swik_widget.get_filename())

        self.config.set_tabs(tabs)
        self.config.flush()
        super().closeEvent(a0)


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

        ChangesTracker.set_view(self.view)

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
        self.key_manager.register_combination_action('Ctrl+A', lambda: self.manager.keyboard('Ctrl+A'))
        self.key_manager.register_combination_action('Ctrl+T', self.manager.get_tool("text_selection").iterate_selection_mode)
        self.key_manager.register_combination_action('Ctrl+M', self.iterate_mode)
        self.key_manager.register_combination_action('Ctrl+Z', ChangesTracker.undo)
        self.key_manager.register_combination_action('Ctrl+Shift+Z', ChangesTracker.redo)

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
        for item in items:
            self.view.scene().removeItem(item)

        ChangesTracker.items_removed(items)

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


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    socket = QUdpSocket()
    socket.bind(QHostAddress.LocalHost, 0)
    socket.open(QUdpSocket.ReadWrite)

    if len(sys.argv) > 1 and window.config.get("open_other_pdf_in") != 1:
        udp_port = utils.are_other_instances_running()
        if udp_port > 0:
            print("Another instance is running, sending filename to it")
            socket.writeDatagram(" ".join(sys.argv[1:]).encode(), QHostAddress.LocalHost, udp_port)
            if socket.waitForReadyRead(1000):
                datagram, host, port = socket.readDatagram(socket.pendingDatagramSize())
                socket.waitForReadyRead()
                datagram, host, port = socket.readDatagram(socket.pendingDatagramSize())
                if datagram.decode() == "QUIT":
                    sys.exit(0)

    def received():
        while socket.hasPendingDatagrams():
            datagram, host, port = socket.readDatagram(socket.pendingDatagramSize())
            socket.writeDatagram("OK".encode(), QHostAddress.LocalHost, port)

            if window.config.get("open_other_pdf_in") == 0 or window.should_open_here(datagram.decode()):
                socket.writeDatagram("QUIT".encode(), QHostAddress.LocalHost, port)
                window.hide()
                window.show()
                window.open_file(datagram.decode())

            else:
                socket.writeDatagram("OPEN".encode(), QHostAddress.LocalHost, port)

    socket.readyRead.connect(received)
    window.show()

    if len(sys.argv) > 1:
        window.open_file(sys.argv[1])

    app.exec_()


if __name__ == "__main__":
    main()
