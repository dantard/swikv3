import os
import subprocess
import sys

from PyQt5.QtNetwork import QUdpSocket, QHostAddress

import resources
import pyclip
from PyQt5 import QtGui
from PyQt5.QtCore import QPointF, Qt, QPoint
from PyQt5.QtGui import QPainter, QIcon, QKeySequence, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut, QFileDialog, QDialog, QMessageBox, QHBoxLayout, QWidget, QTabWidget, QVBoxLayout, QToolBar, \
    QPushButton, QSizePolicy, QTabBar, QMenu

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
from swik_tab_widget import SwikTabWidget
from swik_widget import SwikWidget
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

    TAB_MENU_OPEN_IN_OTHER_TAB = 0
    TAB_MENU_OPEN_IN_OTHER_WINDOW = 1
    TAB_MENU_OPEN_WITH = 2
    TAB_MENU_LOCATE_IN_FOLDER = 3


    def __init__(self):
        super().__init__()

        self.config = SwikConfig()

        ToolSign.configure(self.config)

        self.config.read()

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('Open', self.open_file)
        open_recent = file_menu.addMenu("Open Recent")
        open_recent.aboutToShow.connect(lambda: self.config.fill_recent(self, open_recent))
        file_menu.addAction('Save', self.save_file)
        file_menu.addAction('Save as', self.save_file_as)
        file_menu.addAction('Copy path', lambda: pyclip.copy(self.renderer.filename))
        edit_menu = menu_bar.addMenu('Edit')
        edit_menu.addSeparator()
        edit_menu.addAction('Preferences', self.preferences)

        tool_menu = menu_bar.addMenu('Tools')
        tool_menu.addAction('Flatten', lambda: self.flatten(False))
        tool_menu.addAction('Flatten and Open', lambda: self.flatten(True))
        tool_menu.addSeparator()
        tool_menu.addAction('Append PDF', self.append_pdf)
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

        self.tab_widget = SwikTabWidget()
        self.tab_widget.addTab(QWidget(), "+")
        self.tab_widget.currentChanged.connect(self.tab_changed)
        self.tab_widget.setStyleSheet("QTabBar::tab { max-width: 300px; text-align: right; }")
        self.tab_widget.add_menu_entry("Open copy in other tab", self.TAB_MENU_OPEN_IN_OTHER_TAB)
        self.tab_widget.add_menu_entry("Open copy in other window", self.TAB_MENU_OPEN_IN_OTHER_WINDOW)
        self.tab_widget.add_menu_entry('Locate in folder', self.TAB_MENU_LOCATE_IN_FOLDER)

        # Add open with menu
        command = self.config.get("other_pdf")
        if command is not None and command != "None":
            actions = []
            for line in command.split("&&"):
                data = line.split(" ")
                actions.append((data[0], self.TAB_MENU_OPEN_WITH, data[1]) if len(data)==2 else (data[0], self.TAB_MENU_OPEN_WITH, data[0]))
            self.tab_widget.add_menu_submenu("Open with", actions)
        self.tab_widget.set_menu_callback(self.tab_menu)
        # Done

        self.setCentralWidget(self.tab_widget)

        # Open last files if required
        if self.config.get("open_last"):
            tabs = self.config.get_tabs()
            if len(tabs) == 0:
                self.create_tab()
            else:
                for tab in tabs:
                    self.create_tab(tab)
            self.tab_widget.setCurrentIndex(0)

    def tab_menu(self, action, code, data, widget):
        print("tab_menu", action, code, data, widget)
        filename = widget.get_filename()
        if code == self.TAB_MENU_OPEN_IN_OTHER_TAB:
            self.create_tab(filename)
        elif code == self.TAB_MENU_OPEN_IN_OTHER_WINDOW:
            subprocess.Popen([sys.executable, os.path.realpath(__file__), filename])
        elif code == self.TAB_MENU_OPEN_WITH:
            self.open_with_other(data)
        elif code == self.TAB_MENU_LOCATE_IN_FOLDER:
            os.system(self.config.get("file_browser") + " '" + widget.get_filename() + "' &")

    def get_widgets(self) -> [SwikWidget]:
        return [self.tab_widget.widget(i) for i in range(self.tab_widget.count() - 1)]

    def current(self) -> SwikWidget:
        return self.tab_widget.currentWidget()

    def tab_changed(self, index):
        if index == self.tab_widget.count() - 1:
            self.create_tab(None)
            self.tab_widget.setCurrentIndex(index)
        self.setWindowTitle(
            "Swik" + (" - " + self.tab_widget.currentWidget().get_filename()) if self.tab_widget.currentWidget().get_filename() is not None else "")

    def create_tab(self, filename=None):
        widget = SwikWidget(self, self.tab_widget, self.config)
        self.tab_widget.new_tab(widget, filename)
        if filename is not None:
            widget.open_file(filename)
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
            if (filename:=swik_widget.get_filename()) is not None:
                tabs.append(filename)

        self.config.set_tabs(tabs)
        self.config.flush()
        super().closeEvent(a0)

    # ### TOOLS

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

    def append_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if filename:
            self.current().append_pdf(filename)


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
