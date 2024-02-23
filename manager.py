import queue
import time
from multiprocessing.pool import ThreadPool

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import QMenu, QGraphicsRectItem, QApplication

from renderer import MuPDFRenderer
from rubberband import RubberBand
from selector import SelectorRectItem
from word import MetaWord


class Manager(QObject):
    SELECTION_MODE_NATURAL = 0
    SELECTION_MODE_RECT = 1

    def __init__(self, renderer):
        super(Manager, self).__init__(renderer)
        print("Manager created")
        self.renderer: MuPDFRenderer = renderer
        self.rubberband = None
        self.view = None
        self.selection_mode = Manager.SELECTION_MODE_NATURAL
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
                page = self.view.get_page_item(i)
                if len(page.get_words()) == 0:
                    page.set_words(self.renderer.extract_words(i))
                for word in page.get_words():
                    words.append(word)

            for i, word in enumerate(words):
                word.seq = i
                if word.get_rect_on_scene().intersects(selector.get_rect_on_scene()):
                    self.selected.append(word)

            if len(self.selected) > 1:
                if self.selection_mode == Manager.SELECTION_MODE_NATURAL:
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

        if self.rubberband is None:
            self.clear_selection()
            if self.selection_mode == Manager.SELECTION_MODE_NATURAL:
                self.rubberband = SelectorRectItem(pen=Qt.transparent)
                self.view.setCursor(Qt.IBeamCursor)
            else:
                self.rubberband = SelectorRectItem()
                self.view.setCursor(Qt.CrossCursor)

            self.rubberband.signals.creating.connect(self.selecting)
            self.rubberband.signals.done.connect(self.selecting_done)
            self.view.scene().addItem(self.rubberband)
            self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def context_menu(self, event):
        if len(self.selected) > 0:
            menu = QMenu()
            action = menu.addAction("Copy")
            res = menu.exec(event.globalPos())
            if res == action:
                for word in self.selected:
                    print(word.get_text())


class Finder(QObject):
    MODE_NORMAL = 0
    MODE_Cc = 1
    MODE_W = 2
    MODE_Cc_W = 3

    found = pyqtSignal(list)
    join = pyqtSignal(QGraphicsRectItem)
    progress = pyqtSignal(int)

    def __init__(self, view, renderer):
        super(Finder, self).__init__()
        self.renderer = renderer
        self.view = view
        self.pool = ThreadPool(processes=1)
        self.queue = queue.Queue()
        self.confirmed = []
        self.confirmed_index = 0
        self.mode = Finder.MODE_NORMAL
        self.join.connect(self.set_page_words)
        self.found.connect(self.found_word)

    def set_mode(self, mode):
        self.set_mode(mode)

    def get_mode(self):
        return self.mode

    def find(self, text):
        self.pool.apply_async(self.find_thread, (text,))

    def check_words(self, w1, w2):
        if self.mode == Finder.MODE_NORMAL:
            return w1.lower() in w2.lower()
        elif self.mode == Finder.MODE_Cc:
            return w1 in w2
        elif self.mode == Finder.MODE_W:
            return w1.lower() == w2.lower()
        elif self.mode == Finder.MODE_Cc_W:
            return w1 == w2

    def find_thread(self, text):
        needles = text.split()
        text = needles[0]
        candidates, words = [], []

        for i in range(self.view.get_page(), self.view.get_page() + self.view.get_num_of_pages()):
            page = self.view.get_page_item(i % self.view.get_num_of_pages())

            # Wait until the page is ready
            while not page.has_words():
                self.join.emit(page)
                time.sleep(0.1)

            # Check if the word is in the page
            for word in page.get_words():
                words.append(word)
                if word.get_text().lower() == text.lower():
                    candidates.append((word, len(words) - 1))

            # After processing every page we must check the candidates
            # because the sentence can be split between pages
            for word, index in candidates:

                sentence = [word]
                for j, needle in enumerate(needles[1:]):
                    if index + j + 1 >= len(words) or not self.check_words(needle, words[index + j + 1].get_text()):
                        break
                    sentence.append(words[index + j + 1])
                else:
                    candidates.remove((word, index))
                    self.confirmed.append(sentence)
                    self.found.emit(sentence)

    def set_page_words(self, page):
        words = self.renderer.extract_words(page.index)
        page.set_words(words)

    def found_word(self, sentence):
        for word in sentence:
            word.set_highlighted(True)

    def next(self):
        if len(self.confirmed) > 0:
            self.confirmed_index = (self.confirmed_index + 1) % len(self.confirmed)
            return self.confirmed[self.confirmed_index]
        return []
