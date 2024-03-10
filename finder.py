import threading
import time

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QGraphicsRectItem


class Finder(QObject):
    MODE_NORMAL = 0
    MODE_Cc = 1
    MODE_W = 2
    MODE_Cc_W = 3

    found = pyqtSignal(int)
    join = pyqtSignal(QGraphicsRectItem)
    progress = pyqtSignal(float)

    def __init__(self, view, renderer):
        super(Finder, self).__init__()
        self.renderer = renderer
        self.view = view
        self.confirmed = []
        self.confirmed_index = 0
        self.mode = Finder.MODE_NORMAL
        self.join.connect(self.set_page_words)
        self.thread = None
        self.keep_running = True

    def set_mode(self, mode):
        self.set_mode(mode)

    def get_mode(self):
        return self.mode

    def find(self, text, mode):
        self.mode = mode

        # Joining hypothetical other thread
        if self.thread is not None:
            self.keep_running = False
            self.thread.join()

        self.thread = threading.Thread(target=self.find_thread, args=(text,))
        self.thread.start()

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
        if len(text) == 0:
            return

        self.clear()

        needles = text.split()
        text = needles[0]
        candidates, words = [], []
        self.keep_running = True

        for i in range(self.view.get_num_of_pages()):

            if not self.keep_running:
                return

            page = self.view.get_page_item(i)
            self.progress.emit(i + 1 / (self.view.get_num_of_pages()))

            # Wait until the page is ready
            while not page.has_words():
                self.join.emit(page)
                time.sleep(0.1)

            # Check if the word is in the page
            for word in page.get_words():
                words.append(word)
                if self.check_words(text, word.get_text()):
                    candidates.append((word, len(words) - 1))
                    print(word.get_text(), len(words) - 1)

            # After processing every page we must check the candidates
            # because the sentence can be split between pages
            # WARNING: We are copying the list because we are going to remove elements
            copy = candidates.copy()
            for word, index in copy:
                print(word.get_text(), index, "*")
                sentence = [word]
                for j, needle in enumerate(needles[1:]):
                    if index + j + 1 >= len(words) or not self.check_words(needle, words[index + j + 1].get_text()):
                        print("break", needle, words[index + j + 1].get_text(), word.get_text())
                        break
                    sentence.append(words[index + j + 1])
                else:
                    candidates.remove((word, index))
                    self.confirmed.append(sentence)
                    self.found.emit(len(self.confirmed))

    def set_page_words(self, page):
        words = self.renderer.extract_words(page.index)
        page.set_words(words)

    def next(self, direction):
        for sentence in self.confirmed:
            for word in sentence:
                word.set_highlighted(False)

        if len(self.confirmed) > 0:
            sentence = self.confirmed[self.confirmed_index]
            self.confirmed_index = self.confirmed_index + direction
            self.confirmed_index = self.confirmed_index if self.confirmed_index < len(self.confirmed) else 0
            self.confirmed_index = self.confirmed_index if self.confirmed_index >= 0 else len(self.confirmed) - 1
            for word in sentence:
                word.set_highlighted(True)
                self.view.ensureVisible(word)
            return sentence
        return []

    def get_count(self):
        return len(self.confirmed)

    def get_index(self):
        return self.confirmed_index

    def clear(self):
        for sentence in self.confirmed:
            for word in sentence:
                word.set_highlighted(False)

        self.confirmed.clear()
        self.confirmed_index = 0
        self.progress.emit(0.0)
