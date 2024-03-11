import os
import subprocess
import sys

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QTabWidget, QPushButton, QWidget, QHBoxLayout, QTabBar, QMenu, QAction



class MyAction(QAction):
    def __init__(self, name, code=0, data=None, parent=None):
        super(MyAction, self).__init__(name, parent)
        self.code = code
        self.data = data



class SwikTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super(SwikTabWidget, self).__init__(parent)
        self.setMovable(True)
        self.menu = QMenu()
        self.menu_callback = None

    def add_menu_entry(self, name, code=0, data=None):
        qa = MyAction(name, code, data, self)
        return self.menu.addAction(qa)

    def add_menu_submenu(self, name, actions):
        sub = self.menu.addMenu(name)
        for action in actions:
            data = action[2] if len(action) > 2 else None
            sub.addAction(MyAction(action[0], action[1], data, self))

    def set_menu_callback(self, callback):
        self.menu_callback = callback

    def menu_popup(self, pos, widget):
        res = self.menu.exec(pos)
        if res and self.menu_callback:
            self.menu_callback(res.text(), res.code, res.data, widget)

    def close_tab(self, widget):
        index = self.indexOf(widget)
        if index != -1:
            self.removeTab(index)
            widget.deleteLater()

    def new_tab(self, widget, filename):
        index = self.insertTab(self.count() - 1, widget, filename if filename is not None else "(None)")
        close_button = QPushButton("⨯")
        close_button.setContentsMargins(0, 0, 0, 0)
        close_button.setFixedSize(20, 20)
        close_button.setFlat(True)
        close_button.widget = widget
        close_button.clicked.connect(lambda y, x=widget: self.close_tab(x))

        other_button = QPushButton("▽")
        other_button.setContentsMargins(0, 0, 0, 0)
        other_button.setFixedSize(20, 20)
        other_button.setFlat(True)
        other_button.widget = widget
        other_button.clicked.connect(lambda: self.menu_popup(other_button.mapToGlobal(QPoint(0, 20)), widget))

        widget.a = QWidget()
        widget.a.setLayout(QHBoxLayout())
        widget.a.layout().setContentsMargins(10, 0, 0, 0)
        widget.a.layout().addWidget(other_button)
        widget.a.layout().addWidget(close_button)
        widget.a.layout().setSpacing(0)

        self.tabBar().setTabButton(index, QTabBar.RightSide, widget.a)
        self.setCurrentIndex(index)