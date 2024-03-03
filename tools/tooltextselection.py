from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QMenu, QGraphicsRectItem, QGraphicsScene

from selector import SelectorRectItem
from simplepage import SimplePage
from swiktext import SwikText
from tools.tool import Tool
from word import Word


class TextSelection(Tool):
    SELECTION_MODE_NATURAL = 0
    SELECTION_MODE_RECT = 1

    def __init__(self, view, renderer, config):
        super(TextSelection, self).__init__(view, renderer, config)
        print("Manager created")
        self.rubberband = None
        self.selection_mode = TextSelection.SELECTION_MODE_RECT
        self.selected = []

    def set_view(self, view):
        self.view = view

    def clear_selection(self):
        for word in self.selected:
            word.set_selected(False)
        self.selected.clear()

    def selecting(self, selector: SelectorRectItem):
        p1 = selector.get_rect_on_scene().topLeft()
        p2 = selector.get_rect_on_scene().bottomRight()

        p1_on_view = self.view.mapFromScene(p1)
        p2_on_view = self.view.mapFromScene(p2)

        page1 = self.view.get_page_at_pos(p1_on_view)
        page2 = self.view.get_page_at_pos(p2_on_view)

        print(page1.index, page2.index)

        self.clear_selection()

        if page1 is not None and page2 is not None:

            words = []

            for i in range(page1.index, page2.index + 1):
                print("Page ", i)
                page = self.view.get_page_item(i)
                if page.get_words() is None:
                    page.set_words(self.renderer.extract_words(i))
                for word in page.get_words():
                    words.append(word)

            for i, word in enumerate(words):
                word.seq = i
                if word.get_rect_on_scene().intersects(selector.get_rect_on_scene()):
                    self.selected.append(word)

            if len(self.selected) > 1:
                if self.selection_mode == TextSelection.SELECTION_MODE_NATURAL:
                    # Clear the selection to restore order
                    begin, end = self.selected[0].seq, self.selected[-1].seq
                    self.selected.clear()
                    for i in range(begin, end + 1):
                        words[i].set_selected(True)
                        self.selected.append(words[i])
                else:
                    for word in self.selected:
                        word.set_selected(True)

    def selecting_done(self, selector: SelectorRectItem):
        self.selecting(selector)
        self.view.scene().removeItem(selector)
        self.rubberband = None
        self.view.setCursor(Qt.ArrowCursor)

    def mouse_pressed(self, event):
        if event.button() == Qt.RightButton:
            return

        if not self.view.top_is(event.pos(), [SimplePage, SimplePage.MyImage, Word]):
            return

        if self.rubberband is None:
            self.clear_selection()
            if self.selection_mode == TextSelection.SELECTION_MODE_NATURAL:
                self.rubberband = SelectorRectItem(pen=Qt.transparent)
                self.view.setCursor(Qt.IBeamCursor)
            else:
                self.rubberband = SelectorRectItem()
                self.view.setCursor(Qt.CrossCursor)

            self.rubberband.signals.creating.connect(self.selecting)
            self.view.scene().addItem(self.rubberband)
            self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)
            self.selecting_done(self.rubberband)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def context_menu(self, event):
        menu = QMenu()
        add_text = menu.addAction("Add Text")
        if len(self.selected) > 0:
            copy = menu.addAction("Copy")
            anon = menu.addAction("Anonymyze")
            highlight = menu.addAction("Highlight Annotation")

        res = menu.exec(event.globalPos())
        if res is None:
            pass
        elif res == highlight:
            pass
        elif res == add_text:

            st = SwikText("New Text", self.view.pages[0])
            on_scene = self.view.mapToScene(event.pos())
            st.setPos(st.mapFromScene(on_scene))
            font3 = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
            st.set_ttf_font(font3, 24)

        elif res == copy:
            for word in self.selected:
                print(word.get_text())

    def finish(self):
        self.clear_selection()
        self.view.setCursor(Qt.ArrowCursor)
