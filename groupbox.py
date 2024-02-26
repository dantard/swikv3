from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QButtonGroup, QPushButton, QToolBar, QAction

class GroupButton(QPushButton):
    def __init__(self, tool=None):
        super().__init__()
        self.tool = tool
    def get_tool(self):
        return self.tool

class GroupBox:
    def __init__(self):
        self.buttons = []
        self.group = QButtonGroup()
        self.default = None

    def reclick(self):
        for btn in self.buttons:
            if btn.isChecked():
                print("re-fucking-click")
                btn.click()
                break

    def on_any_button_clicked(self, callback):
        self.group.buttonClicked.connect(callback)

    def add(self, callback, default=False, text="", icon=None, tool=None):
        btn = GroupButton(tool)
        btn.setContentsMargins(0, 0, 0, 0)
        btn.setIconSize(QSize(24, 24))
        btn.setFlat(True)
        btn.setCheckable(True)
        if callback is not None:
            btn.clicked.connect(callback)

        if (icon := QIcon(icon)) is not None:
            btn.setIcon(icon)
            btn.setToolTip(text)
        else:
            btn.setText(text)
        btn.setToolTip(text)
        if default:
            btn.setChecked(True)
            self.default = btn
        self.buttons.append(btn)
        self.group.addButton(btn)
        return btn

    def click(self, value):
        self.buttons[value].click()

    def reset(self):
        self.default.click()

    def get_selected(self):
        for i, btn in enumerate(self.buttons):
            if btn.isChecked():
                return i

    def append(self, toolbar: QToolBar):
        for btn in self.buttons:
            toolbar.addWidget(btn)
