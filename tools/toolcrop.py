from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMenu

from action import Action
from interfaces import Undoable
from selector import SelectorRectItem
from simplepage import SimplePage
from tools.tool import Tool
from word import Word


class ToolCrop(Tool, Undoable):

    def __init__(self, view, renderer, config):
        super(ToolCrop, self).__init__(view, renderer, config)
        self.rubberband = None

    def mouse_pressed(self, event):
        if event.button() == Qt.RightButton:
            return

        page = self.view.get_page_at_pos(event.pos())
        if page is None:
            return

        if self.rubberband is None:
            self.rubberband = SelectorRectItem(page)
            self.view.setCursor(Qt.CrossCursor)
            self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            page = self.rubberband.parentItem()
            self.rubberband.view_mouse_release_event(self.view, event)
            before = self.renderer.get_cropbox(page.index)
            print("before CB", before)
            self.renderer.set_cropbox(page.index, self.rubberband.get_rect_on_parent(), self.view.get_ratio())
            after = self.renderer.get_cropbox(page.index)
            print("after CB", after)
            self.view.scene().removeItem(self.rubberband)
            self.rubberband = None
            self.notify_any_change(Action.ACTION_CHANGED, (page.index, before, 1), (page.index, after, 1), self.view.scene())
            print("BEFORE AFTER", before, after)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def context_menu(self, event):
        pass

    def finish(self):
        self.view.setCursor(Qt.ArrowCursor)

    def undo(self, kind, info):
        index, rect, ratio = info
        print(info, "undo cropbox")
        self.renderer.set_cropbox(index, rect, ratio, True)

    def redo(self, kind, info):
        self.undo(kind, info)
