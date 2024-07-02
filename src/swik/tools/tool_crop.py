from PyQt5.QtCore import Qt

from swik.action import Action
from swik.annotations.annotation import Annotation
from swik.annotations.hyperlink import Link
from swik.annotations.redact_annotation import RedactAnnotation
from swik.interfaces import Undoable
from swik.selector import SelectorRectItem
from swik.simplepage import SimplePage
from swik.tools.tool import Tool
from swik.word import Word


class ToolCrop(Tool, Undoable):

    def __init__(self, widget):
        super(ToolCrop, self).__init__(widget)
        self.rubberband = None

    def mouse_pressed(self, event):
        if event.button() == Qt.RightButton:
            return

        if self.view.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return

        page = self.view.get_page_at_pos(event.pos())
        if page is None:
            return

        if self.rubberband is None:
            self.view.setCursor(Qt.CrossCursor)
            self.rubberband = SelectorRectItem(page, event=(self.view, event))
            self.rubberband.signals.done.connect(self.selection_done)
            #self.rubberband.view_mouse_press_event(self.view, event)

    def selection_done(self, rb):
        if rb.get_rect_on_parent().width() > 5 and rb.get_rect_on_parent().height() > 5:

            # Remove items outside the cropbox or move those inside
            page = self.rubberband.parentItem()
            items = self.view.pages[page.index].items((Link, Annotation, RedactAnnotation))
            for item in items:
                if not self.rubberband.get_rect_on_parent().contains(item.pos()):
                    self.view.scene().removeItem(item)
                else:
                    item.setPos(item.pos().x() - self.rubberband.get_rect_on_parent().x(), item.pos().y() - self.rubberband.get_rect_on_parent().y())

            # Apply the cropbox
            before = self.renderer.get_cropbox(page.index)
            self.renderer.set_cropbox(page.index, self.rubberband.get_rect_on_parent(), False)
            after = self.renderer.get_cropbox(page.index)
            self.notify_any_change(Action.ACTION_CHANGED, (page.index, before, 1), (page.index, after, 1), self.view.scene())

        self.view.scene().removeItem(self.rubberband)
        self.rubberband = None

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)

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
