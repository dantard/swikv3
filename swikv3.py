import os
import subprocess
import sys

from PyQt5.QtNetwork import QUdpSocket, QHostAddress

import resources
import pyclip
from PyQt5 import QtGui
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QPainter, QIcon, QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut, QFileDialog, QDialog, QMessageBox, QHBoxLayout

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

        self.setWindowTitle("Swik")
        self.setGeometry(100, 100, 640, 480)
        self.setAcceptDrops(True)

        self.renderer = MuPDFRenderer()
        self.renderer.document_changed.connect(self.document_changed)

        self.scene = Scene()
        self.manager = Manager(self.renderer, self.config)
        self.view = SwikGraphView(self.manager, self.renderer, self.scene, page=Page, mode=self.config.get('mode', LayoutManager.MODE_VERTICAL))
        self.manager.set_view(self.view)

        ChangesTracker.set_view(self.view)

        self.font_manager = FontManager(self.renderer)
        # self.font_manager.update_system_fonts()
        self.font_manager.update_swik_fonts()

        self.manager.register_tool('text_selection', TextSelection(self.view, self.renderer, self.font_manager, self.config), True)
        self.manager.register_tool('sign', ToolSign(self.view, self.renderer, self.config), False)
        self.manager.register_tool('rearrange', ToolRearrange(self.view, self.renderer, self.config), False)
        self.manager.register_tool('redact_annot', ToolRedactAnnotation(self.view, self.renderer, self.config), False)
        self.manager.register_tool('square_annot', ToolSquareAnnotation(self.view, self.renderer, self.config), False)
        self.manager.register_tool('crop', ToolCrop(self.view, self.renderer, self.config), False)
        self.manager.register_tool('drag', ToolDrag(self.view, self.renderer, self.config), False)

        self.key_manager = KeyboardManager(self)
        self.key_manager.register_action(Qt.Key_Shift, lambda: self.manager.use_tool("drag"), self.manager.finished)
        self.key_manager.register_combination_action('Ctrl+A', self.manager.get_tool("text_selection").iterate_selection_mode)
        self.key_manager.register_combination_action('Ctrl+M', self.iterate_mode)
        self.key_manager.register_combination_action('Ctrl+Z', ChangesTracker.undo)
        self.key_manager.register_combination_action('Ctrl+Shift+Z', ChangesTracker.redo)

        self.config.load("swik.yaml")

        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.TextAntialiasing)
        self.view.set_natural_hscroll(self.config.get('natural_hscroll'))

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('Open', self.open_file)
        open_recent = file_menu.addMenu("Open Recent")
        open_recent.aboutToShow.connect(lambda: self.config.fill_recent(self, open_recent))
        file_menu.addAction('Save', self.save_file)
        file_menu.addAction('Save as', self.save_file_as)
        file_menu.addAction('Locate in folder', lambda: os.system(self.config.get("file_browser") + " '" + self.renderer.get_filename() + "' &"))
        file_menu.addAction('Copy path', lambda: pyclip.copy(self.renderer.filename))
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

        edit_menu = menu_bar.addMenu('Edit')
        edit_menu.addSeparator()
        edit_menu.addAction('Preferences', self.preferences)

        tool_menu = menu_bar.addMenu('Tools')
        tool_menu.addAction('Flatten', lambda: self.flatten(False))
        tool_menu.addAction('Flatten and Open', lambda: self.flatten(True))
        tool_menu.addSeparator()
        tool_menu.addAction('Extract Fonts', self.extract_fonts)

        self.toolbar = self.addToolBar('Toolbar')
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

        self.nav_toolbar = NavigationToolbar(self.view, self.toolbar)
        self.finder_toolbar = TextSearchToolbar(self.view, self.renderer, self.toolbar)
        self.statusBar().show()
        self.setCentralWidget(self.view)

        if self.config.get("open_last"):
            last = self.config.get('last', None)
            if last is not None:
                self.renderer.open_pdf(last)

    info = {}

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
        self.setWindowTitle("Swik - " + self.renderer.get_filename())
        self.font_manager.update_document_fonts()

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

    def save_file(self):
        self.renderer.save_pdf(self.renderer.get_filename())

    def save_file_as(self):
        pass

    def preferences(self):
        self.config.exec()
        self.sign_btn.setEnabled(self.config.get("p12") is not None)
        self.config.flush()

    def open_with_other(self, command):
        if command is not None:
            os.system(command + " '" + self.renderer.get_filename() + "' &")
        else:
            self.config.edit()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.config.save("swik.yaml")
        super().closeEvent(a0)

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
