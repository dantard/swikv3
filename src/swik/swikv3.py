#!/usr/bin/env python
import argparse
import os
import subprocess
import sys
import dbus.mainloop.glib

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

from PyQt5 import QtGui
from PyQt5.QtCore import QEvent, QThread, pyqtSignal, QObject, Qt
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtNetwork import QUdpSocket, QHostAddress
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog

import swik.utils as utils
from swik.dialogs import DeveloperInfoDialog
from swik.layout_manager import LayoutManager
from swik.magnifier import Magnifier
from swik.progressing import Progressing
from swik.swik_dbus import DBusServerThread
from swik.swik_tab_widget import SwikTabWidget
from swik.swik_widget import SwikWidget
from swik.swik_config import SwikConfig


class MainWindow(QMainWindow):
    TAB_MENU_OPEN_IN_OTHER_TAB = 0
    TAB_MENU_OPEN_IN_OTHER_WINDOW = 1
    TAB_MENU_OPEN_WITH = 2
    TAB_MENU_LOCATE_IN_FOLDER = 3

    def __init__(self):
        super().__init__()

        self.config = SwikConfig()
        self.config.read()
        menu_bar = self.menuBar()

        # Setup file menu
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('Open', self.open_file)
        open_recent = file_menu.addMenu("Open Recent")
        file_menu.addAction("Import", self.import_file)
        file_menu.addSeparator()
        open_recent.aboutToShow.connect(lambda: self.config.fill_recent(self, open_recent))
        save = file_menu.addAction('Save', self.save_file)
        save_as = file_menu.addAction('Save as', self.save_file_as)

        rename = file_menu.addAction('Rename', self.rename)
        file_menu.addSeparator()
        copy_path = file_menu.addAction('Copy path', self.copy_path)
        command = self.config.general.get("other_pdf")
        self.file_menu_actions = [save, save_as, copy_path, rename]

        if command is not None and command != "None":
            open_wo_odf = file_menu.addMenu('Open with other Viewer')
            self.file_menu_actions.append(open_wo_odf)
            for line in command.split("&&"):
                data = line.split(" ")
                if len(data) == 2:
                    name, cmd = data
                else:
                    name = cmd = data[0]
                open_wo_odf.addAction(name, lambda x=cmd: self.open_with_other(x))
        # end setup file menu

        # Setup edit menu
        self.edit_menu = menu_bar.addMenu('Edit')
        self.edit_menu.addAction('Edit metadata', lambda: self.current().edit_metadata())
        self.edit_menu.addAction('Edit XML metadata', lambda: self.current().edit_xml_metadata())
        self.edit_menu.addSeparator()
        self.edit_menu.addAction('Preferences', self.preferences)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction('Set as default PDF reader', self.set_as_default)
        # end setup edit menu

        # Setup tools menu
        self.tool_menu = menu_bar.addMenu('Tools')
        self.tool_menu.addAction('Magnifier', self.show_magnifier)
        self.tool_menu.addSeparator()
        self.tool_menu.addAction('Flatten', lambda: self.flatten(False))
        self.tool_menu.addAction('Flatten and Open', lambda: self.flatten(True))
        self.tool_menu.addSeparator()
        self.tool_menu.addAction('Extract Fonts', self.extract_fonts)
        # end setup tools menu

        self.about_menu = menu_bar.addMenu('Help')
        self.about_menu.addAction('About', self.about)

        self.setWindowTitle("Swik")
        self.setGeometry(100, 100, 640, 480)

        self.tab_widget = SwikTabWidget()
        # self.tab_widget.addTab(QWidget(), "+")
        self.tab_widget.currentChanged.connect(self.tab_changed)
        self.tab_widget.setStyleSheet("QTabBar::tab { max-width: 300px; text-align: right; }")
        self.tab_widget.add_menu_entry("Open copy in other tab", self.TAB_MENU_OPEN_IN_OTHER_TAB)
        self.tab_widget.add_menu_entry("Open copy in other window", self.TAB_MENU_OPEN_IN_OTHER_WINDOW)
        self.tab_widget.add_menu_entry('Locate in folder', self.TAB_MENU_LOCATE_IN_FOLDER)
        self.tab_widget.plus_clicked.connect(self.plus_clicked)
        self.tab_widget.tab_close_requested.connect(self.close_tab)

        # Add open with menu
        command = self.config.general.get("other_pdf")
        if command is not None and command != "None":
            actions = []
            for line in command.split("&&"):
                data = line.split(" ")
                actions.append((data[0], self.TAB_MENU_OPEN_WITH, data[1]) if len(data) == 2 else (
                    data[0], self.TAB_MENU_OPEN_WITH, data[0]))
            self.tab_widget.add_menu_submenu("Open with", actions)
        self.tab_widget.set_menu_callback(self.tab_menu)
        # Done

        # self.tab_widget.setVisible(False)
        self.magnifier = None
        self.setCentralWidget(self.tab_widget)
        self.config.apply_window_config(self)
        self.update_interaction_status()
        self.show()

    def import_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Import file", "",
                                                   "Supported files (*.doc *.docx *.odt *.rtf *.html *.htm *.xml *.pptx *.ppt *.xls *.xlsx *.png *.jpg *.jpeg "
                                                   "*.bmp *.gif *.tiff *.pnm *.pgm *.ppm *.xps *.svg *.epub *.mobi *.txt)")
        if file_name:
            self.open_file(file_name)

    def about(self):
        DeveloperInfoDialog().exec()

    def show_magnifier(self):
        self.magnifier = Magnifier(self.current())
        self.magnifier.show()

    def set_as_default(self):
        utils.add_mimeapps_entry("[Default Applications]", "swik0.3.desktop")
        utils.add_mimeapps_entry("[Added Associations]", "swik0.3.desktop")

    def restore(self):
        if self.config.general.get("open_last"):
            self.progress = Progressing(None, 0, "Opening", True)
            # utils.delayed(100, self.open_tabs)
            self.progress.start(self.open_tabs)

    def open_tabs(self):

        # Open last files if required. This is done
        # with a delay to allow the window to create
        # tabs first and ALSO to show the window if
        # some files has a password dialog to show
        tabs = self.config.get_tabs()
        tabs = tabs if tabs is not None else {}

        for filename, values in tabs.items():
            if self.progress.wasCanceled():
                break
            widget = self.create_widget()

            # Not especially happy with this but it seems to work
            # widget.view.append_on_document_ready(0, widget.view.set_ratio, zoom, True)
            # widget.view.append_on_document_ready(0, widget.view.set_page, page)
            # widget.miniature_view.append_on_document_ready(0, widget.miniature_view.set_page, page)
            widget.view.set_mode(values[1])
            if values[1] != LayoutManager.MODE_FIT_WIDTH:
                widget.view.set_ratio(values[2], True)

            self.open_new_tab(widget, values[0])

            if values[1] != LayoutManager.MODE_SINGLE_PAGE:
                widget.view.set_scroll_value(values[3])
            else:
                widget.view.move_to_page(values[3])

            if len(values) > 4:
                widget.splitter.setSizes(values[4])

        self.tab_widget.setCurrentIndex(0)
        self.update_title()
        self.progress.close()

    def plus_clicked(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if filename:
            widget = self.create_widget()
            self.open_new_tab(widget, filename)

    def open_requested_by_dbus(self, filename):
        filenames = filename.split("*")
        for filename in filenames:
            widget = self.create_widget()
            self.open_new_tab(widget, filename)
        self.raise_()

    def create_widget(self, mode=LayoutManager.MODE_VERTICAL):
        widget = SwikWidget(self, self.config)
        widget.set_mode(mode)
        widget.interaction_changed.connect(self.update_interaction_status)
        widget.open_requested.connect(self.open_requested_by_tab)
        widget.close_requested.connect(self.close_requested_by_tab)
        widget.file_changed.connect(self.update_tab_text)
        widget.dirtiness_changed.connect(self.dirtiness_changed)
        return widget

    def dirtiness_changed(self, widget, dirty):
        self.update_tab_text(widget)
        self.update_title()

    def tab_menu(self, action, code, data, widget):
        print("tab_menu", action, code, data, widget)
        filename = widget.get_filename()
        if code == self.TAB_MENU_OPEN_IN_OTHER_TAB:
            self.open_new_tab(filename)
        elif code == self.TAB_MENU_OPEN_IN_OTHER_WINDOW:
            subprocess.Popen([sys.executable, os.path.realpath(__file__), filename])
        elif code == self.TAB_MENU_OPEN_WITH:
            self.open_with_other(data)
        elif code == self.TAB_MENU_LOCATE_IN_FOLDER:
            os.system(self.config.get("file_browser") + " '" + widget.get_filename() + "' &")

    def get_widgets(self) -> [SwikWidget]:
        return [self.tab_widget.widget(i) for i in range(self.tab_widget.count())]

    def current(self) -> SwikWidget:
        return self.tab_widget.currentWidget()

    def tab_changed(self, index):
        self.update_title()
        if self.magnifier is not None:
            self.magnifier.set_widget(self.current())

    #        self.removeEventFilter(self.current_event_filter)
    #        self.installEventFilter(self.current())
    #        self.current_event_filter = self.current()

    def copy_path(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.current().get_filename())

    def update_title(self):
        asterisk = "*" if self.current() and self.current().is_dirty() else ""
        title = "Swik"
        if self.tab_widget.currentWidget() is not None and self.tab_widget.currentWidget().get_filename() is not None:
            title += " - " + self.tab_widget.currentWidget().get_filename() + asterisk
        self.setWindowTitle(title)
        self.update_interaction_status()

    def update_tab_text(self, widget):
        asterisk = "*" if widget and widget.is_dirty() else ""
        my_index = self.tab_widget.indexOf(widget)
        text = os.path.basename(widget.get_filename())
        font_metrics = self.tab_widget.fontMetrics()
        text = font_metrics.elidedText(text, Qt.ElideRight, 200)
        self.tab_widget.setTabText(my_index, text + asterisk)
        self.tab_widget.setTabToolTip(my_index, widget.get_filename() + asterisk)

    def update_interaction_status(self):
        value = self.current().is_interaction_enabled() if self.current() is not None else False
        self.tool_menu.setEnabled(value)
        # self.edit_menu.setEnabled(self.current().is_interaction_enabled())
        for action in self.file_menu_actions:
            action.setEnabled(value)

    def open_new_tab(self, widget, filename=None):
        self.tab_widget.new_tab(widget, filename)
        if filename is not None:
            widget.open_file(filename)
            self.update_interaction_status()

        return widget

    def open_requested_by_tab(self, filename, page, zoom):
        widget = self.create_widget()
        self.open_new_tab(widget, filename)
        widget.view.set_ratio(zoom, True)
        widget.view.set_page(page)

    def close_requested_by_tab(self, widget):
        self.close_tab(widget)

    def close_tab(self, tab):
        self.tab_widget.close_tab(tab)
        self.update_title()

        # filename = self.tab_widget.currentWidget().get_filename()
        # self.setWindowTitle("Swik" + (" - " + filename) if filename is not None else "")

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        tabs = {}
        for index in range(self.tab_widget.count()):
            swik_widget = self.tab_widget.widget(index)
            if (filename := swik_widget.get_filename()) is not None:
                if swik_widget.view.get_mode() != LayoutManager.MODE_SINGLE_PAGE:
                    value = swik_widget.view.get_scroll_value()
                else:
                    value = swik_widget.view.page
                tabs[index] = [filename, swik_widget.view.get_mode(), swik_widget.view.get_ratio(), value, swik_widget.splitter.sizes()]

        if self.magnifier is not None:
            self.magnifier.close()
            self.magnifier.deleteLater()

        self.config.set_tabs(tabs)
        self.config.push_window_config(self)
        self.config.flush()
        super().closeEvent(a0)

    # ### TOOLS

    def open_file(self, filename=None):
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")

        if filename:
            if self.current() is not None:
                self.current().open_file(filename)
            else:
                self.open_new_tab(self.create_widget(), filename)

    def save_file(self):
        self.current().save_file()

    def save_file_as(self):
        self.current().save_file_as()

    def rename(self):
        self.current().rename()

    def flatten(self, open):
        self.current().flatten(open)

    def extract_fonts(self):
        self.current().extract_fonts()

    def preferences(self):
        self.config.exec()
        self.config.flush()

    def open_with_other(self, command):
        self.current().open_with_other(command)

    def eventFilter(self, a0, a1) -> bool:

        return False

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(a0)


def main():
    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser(description='PDF Swik')
    parser.add_argument('-f', '--force-new-instance', action='store_true')
    parser.add_argument('-t', '--tool', default=None, type=str)
    args, unknown = parser.parse_known_args()

    if len(unknown) > 0 and not args.force_new_instance:
        DBusGMainLoop(set_as_default=True)

        bus = dbus.SessionBus()
        try:
            proxy = bus.get_object('com.swik.server', '/com/swik/server')
            interface = dbus.Interface(proxy, 'com.swik.server_interface')
            print("Requesting running instance to open2222", unknown[0])
            response = interface.open("*".join([os.path.abspath(u) for u in unknown]))
            print("response:", response)
            sys.exit(0)
        except Exception as e:
            print(e)
            print("No other instance running")

    window = MainWindow()

    dbus_loop = DBusServerThread()
    dbus_loop.open_requested.connect(window.open_requested_by_dbus)
    dbus_loop.start()

    app.installEventFilter(window)

    if not args.force_new_instance:
        window.restore()

    if len(unknown) > 0:
        def open_new():
            for u in unknown:
                widget = window.create_widget()
                window.open_new_tab(widget, u)
                widget.set_tool(args.tool)

        # Delayed to avoid it to be opened
        # before the restored tabs
        utils.delayed(25, open_new)
    app.setWindowIcon(QIcon(":/icons/swiss_knife.png"))
    app.exec_()


if __name__ == "__main__":
    main()
