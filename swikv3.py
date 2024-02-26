import os
import sys

import pyclip
from PyQt5 import QtGui
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPainter, QIcon, QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut

from GraphView import GraphView
from LayoutManager import LayoutManager
from groupbox import GroupBox
from manager import Manager
from tools.toolrearranger import ToolRearrange
from tools.toolredactannotation import ToolRedactAnnotation
from tools.toolsign import ToolSign
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

        self.manager = Manager(self.renderer, self.config)
        self.view = GraphView(self.manager, self.renderer, self.config.get('mode', LayoutManager.MODE_VERTICAL), page=Page)
        self.manager.set_view(self.view)

        self.manager.add_tool('text_selection', TextSelection(self.view, self.renderer, self.config), True)
        self.manager.add_tool('sign', ToolSign(self.view, self.renderer, self.config), False)
        self.manager.add_tool('rearrange', ToolRearrange(self.view, self.renderer, self.config), False)
        self.manager.add_tool('redact_annot', ToolRedactAnnotation(self.view, self.renderer, self.config), False)

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

        self.toolbar = self.addToolBar('Toolbar')
        self.toolbar.addAction("Open", self.open_file).setIcon(QIcon(":/icons/open.png"))
        self.toolbar.addAction("Save", self.save_file).setIcon(QIcon(":/icons/save.png"))
        self.toolbar.addSeparator()

        self.mode_group = GroupBox()
        self.mode_group.add(self.manage_tool, True, icon=":/icons/text_cursor.png", text="Select Text", tool="text_selection")
        self.mode_group.add(self.manage_tool, icon=":/icons/sign.png", text="Sign", tool="sign")
        self.mode_group.add(self.manage_tool, icon=":/icons/white.png", text="Anonymize", tool="redact_annot")
        self.mode_group.add(self.manage_tool, icon=":/icons/shuffle.png", text="Shuffle Pages", tool="rearrange")

        self.mode_group.append(self.toolbar)
        self.manager.tool_finished.connect(self.mode_group.reset)

        self.nav_toolbar = NavigationToolbar(self.view, self.toolbar)
        self.finder_toolbar = TextSearchToolbar(self.view, self.renderer, self.toolbar)

        self.setCentralWidget(self.view)

        x_mode = QShortcut(QKeySequence('Ctrl+C'), self)
        x_mode.activated.connect(self.copy)


        self.renderer.open_pdf("/home/danilo/Documents/ADESIONE_2312235026.pdf")
        # self.renderer.open_pdf("/home/danilo/Desktop/swik-files/view.pdf")
    def copy(self):
        selected = self.view.scene().selectedItems()
        for item in selected:
            kind = type(item)
            print("Creating ", kind, " from ", item, " with ", item.get_kwargs())
            obj = kind(copy=item)
            obj.setPos(item.pos() + QPointF(20, 20))



    def document_changed(self):
        self.setWindowTitle("Swik - " + self.renderer.get_filename())

    def manage_tool(self):
        button = self.sender()
        if button is not None:
            self.manager.use_tool(button.get_tool())

    def open_file(self):
        pass

    def save_file(self):
        pass

    def save_file_as(self):
        pass

    def preferences(self):
        self.config.exec()

    def open_with_other(self, command):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.config.save("swik.yaml")
        super().closeEvent(a0)


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
