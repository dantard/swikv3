from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtWidgets import QTabWidget, QPushButton, QWidget, QHBoxLayout, QTabBar, QMenu, QAction, QLabel


class MyAction(QAction):
    def __init__(self, name, code=0, data=None, parent=None):
        super(MyAction, self).__init__(name, parent)
        self.code = code
        self.data = data


class SwikTabWidget(QTabWidget):
    plus_clicked = pyqtSignal()
    tab_close_requested = pyqtSignal(QWidget)

    def __init__(self, parent=None):
        super(SwikTabWidget, self).__init__(parent)
        self.setMovable(True)
        self.menu = QMenu()
        self.menu_callback = None
        self.paint_shortcuts = True

        class PB(QWidget):
            def __init__(self, text, parent=None):
                super(PB, self).__init__(parent)
                self.setLayout(QHBoxLayout())
                self.layout().addWidget(QLabel(" ", self))
                self.pb = QPushButton(text, self)
                self.pb.setFixedSize(20, 20)
                self.layout().addWidget(self.pb)
                self.pb.setVisible(True)
                self.pb.setContentsMargins(0, 0, 5, 8)
                self.layout().setContentsMargins(0, 0, 5, 5)

        pb = PB("+")
        pb.pb.clicked.connect(self.plus_clicked.emit)
        self.setCornerWidget(pb, Qt.TopRightCorner)
        self.plusButton = QPushButton("+", self)
        self.plusButton.clicked.connect(self.plus_clicked.emit)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        if self.paint_shortcuts:
            painter = QPainter(self)
            painter.setFont(QFont('Monospace', 10))

            # Example: Drawing text in the center of the tab widget
            text = "Custom Paint on QTabWidget"
            painter.drawText(QRect(30, 30, self.rect().width() - 30, self.rect().height() - 30),
                             Qt.AlignLeft, "Shortcuts:\n"
                                           " CTRL-B:  Change toolbar position\n"
                                           " CTRL-F:  Search text\n"
                                           " CTRL-M:  Change visualization mode\n"
                                           " CTRL-R:  Reload current file\n\n"
                                           "In Text Selection Tool:\n"
                                           " CTRL-A:  Select all page text\n"
                                           " CTRL-T:  Toggle text selection mode\n\n"
                                           "In Form Tool:\n"
                                           " CTRL-Q:  Toogle page preview\n")

            painter.end()
        else:
            super().paintEvent(a0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.move_plus_button()

    def setTabText(self, index: int, a1: str) -> None:
        super().setTabText(index, a1)
        self.move_plus_button()

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
        self.menu.setEnabled(widget.get_filename() is not None)
        res = self.menu.exec(pos)
        if res and self.menu_callback:
            self.menu_callback(res.text(), res.code, res.data, widget)

    def close_tab_request(self, widget):
        self.tab_close_requested.emit(widget)

    def close_tab(self, widget):
        index = self.indexOf(widget)
        if index != -1:
            self.removeTab(index)
            widget.die()
            widget.deleteLater()

        self.check_paint_shortcuts()

    def removeTab(self, index: int) -> None:
        super().removeTab(index)
        self.move_plus_button()
        self.check_paint_shortcuts()

    def addTab(self, widget: QWidget, a1: str) -> int:
        index = super().addTab(widget, a1)
        self.move_plus_button()
        self.check_paint_shortcuts()
        return index

    def check_paint_shortcuts(self):
        self.paint_shortcuts = self.count() == 0
        self.paint_shortcuts and self.update()

    def insertTab(self, index: int, widget: QWidget, a1: str) -> None:
        index = super().insertTab(index, widget, a1)
        self.move_plus_button()
        self.check_paint_shortcuts()
        return index

    def new_tab(self, widget, filename):
        index = self.addTab(widget, filename if filename is not None else "(None)")
        close_button = QPushButton("⨯")
        close_button.setContentsMargins(0, 0, 0, 0)
        close_button.setFixedSize(20, 20)
        close_button.setFlat(True)
        close_button.widget = widget
        close_button.clicked.connect(lambda y, x=widget: self.close_tab_request(x))
        '''
        other_button = QPushButton("▽")
        other_button.setContentsMargins(0, 0, 0, 0)
        other_button.setFixedSize(20, 20)
        other_button.setFlat(True)
        other_button.widget = widget
        other_button.clicked.connect(lambda: self.menu_popup(other_button.mapToGlobal(QPoint(0, 20)), widget))
        '''
        widget.a = QWidget()
        widget.a.setLayout(QHBoxLayout())
        widget.a.layout().setContentsMargins(10, 0, 0, 0)
        # widget.a.layout().addWidget(other_button)
        widget.a.layout().addWidget(close_button)
        widget.a.layout().setSpacing(0)

        self.tabBar().setTabButton(index, QTabBar.RightSide, widget.a)
        self.setCurrentIndex(index)
        self.move_plus_button()

    def move_plus_button(self):
        xpos = 0
        for i in range(self.tabBar().count()):
            rect = self.tabBar().tabRect(i)
            xpos += rect.width()
        self.plusButton.setGeometry(xpos + 5, 5, 20, 20)
        if xpos > self.width() - 35:
            self.plusButton.hide()
            self.cornerWidget().show()
        else:
            self.plusButton.show()
            self.cornerWidget().hide()

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(a0)
        if a0.button() == Qt.MidButton:
            tab = self.tabBar().tabAt(a0.pos())
            self.close_tab(self.widget(tab))
