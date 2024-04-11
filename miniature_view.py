from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QGraphicsView

import utils
from GraphView import GraphView
from LayoutManager import LayoutManager
from miniature_page import MiniaturePage
from simplepage import SimplePage


class MiniatureView(GraphView):

    def __init__(self, manager, renderer, scene):
        super(MiniatureView, self).__init__(manager, renderer, scene, page=MiniaturePage, mode=LayoutManager.MODE_VERTICAL)

    def wheelEvent(self, event: 'QGraphicsSceneWheelEvent') -> None:
        super(QGraphicsView, self).wheelEvent(event)

    def set_page(self, index):
        self.clear_selection()
        if self.pages.get(index) is not None:
            self.pages[index].set_highlighted(True)
            self.centerOn(self.pages[index])
        #utils.delayed(100, self.centerOn, self.pages[index])

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
                print("Page clicked: ", page.index)
