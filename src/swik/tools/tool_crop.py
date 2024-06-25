from PyQt5.QtCore import Qt

from swik.action import Action
from swik.annotations.hyperlink import Link
from swik.interfaces import Undoable
from swik.selector import SelectorRectItem
from swik.tools.tool import Tool


class ToolCrop(Tool, Undoable):

    def __init__(self, widget):
        super(ToolCrop, self).__init__(widget)
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
            items =  self.view.pages[page.index].items(Link)
            pos_on_orig_page = {}
            for item in items:
                pos_on_orig_page[item] = item.pos()
                print("pos", item.pos(), type(item))

            before = self.renderer.get_cropbox(page.index)
            self.renderer.set_cropbox(page.index, self.rubberband.get_rect_on_parent(), False)
            after = self.renderer.get_cropbox(page.index)

            for k, v in pos_on_orig_page.items():
                if v.x() < after.x() or v.y() < after.y() or v.x() > after.x() + after.width() or v.y() > after.y() + after.height():
                    print("removing", k, v, after.x(), after.y(), after.width(), after.height())
                    self.view.scene().removeItem(k)
                else:
                    k.setPos(v.x() - after.x(), v.y() - after.y())
                    print("keeping", k, v, after.x(), after.y(), after.width(), after.height())

            self.view.scene().removeItem(self.rubberband)
            self.rubberband = None
            self.notify_any_change(Action.ACTION_CHANGED, (page.index, before, 1), (page.index, after, 1), self.view.scene())

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
        self.renderer.set_cropbox(index, rect, True)

    def redo(self, kind, info):
        self.undo(kind, info)
