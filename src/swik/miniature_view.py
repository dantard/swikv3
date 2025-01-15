from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QGraphicsView

from swik.graphview import GraphView
from swik.miniature_page import MiniaturePage
from swik.simplepage import SimplePage


class MiniatureView(GraphView):

    def __init__(self, manager, renderer, scene):
        super(MiniatureView, self).__init__(manager, renderer, scene,
                                            page=MiniaturePage, mode=GraphView.MODE_FIT_WIDTH,
                                            align=QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, page_sep=60)

    def wheelEvent(self, event: 'QGraphicsSceneWheelEvent') -> None:
        super(QGraphicsView, self).wheelEvent(event)

    def move_to_page(self, index, offset=None):
        if super().move_to_page(index, offset):
            for p in self.pages.values():
                p.set_highlighted(False)
            self.pages[index].set_highlighted(True)
            self.ensureVisible(self.pages[index])

    def eventFilter(self, a0: QtCore.QObject, a1: QtCore.QEvent) -> bool:
        if not super().eventFilter(a0, a1):
            if a1.type() == QKeyEvent.KeyPress:
                if a1.key() == Qt.Key_Up:
                    self.move_to_page(self.page - 1)
                    return True
                elif a1.key() == Qt.Key_Down:
                    self.move_to_page(self.page + 1)
                    return True
        return False

    def set_page(self, index):
        self.clear_selection()
        if self.pages.get(index) is not None:
            self.pages[index].set_highlighted(True)
            self.centerOn(self.pages[index])

    def clear_selection(self):
        for p in self.pages.values():
            p.set_highlighted(False)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:

            self.clear_selection()

            page = self.get_items_at_pos(event.pos(), SimplePage, 0, False)

            if page is not None:
                self.page_clicked.emit(page.index)
                page.set_highlighted(True)
