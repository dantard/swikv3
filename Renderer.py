import traceback

import fitz
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QMutex
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QLabel


class Image:
    def __init__(self, w, h):
        self.image = QPixmap(int(w), int(h))
        self.ratio = 1
        self.loaded = False
        self.image.fill(Qt.white)
        self.w = w
        self.h = h

    def update(self, w, h):
        self.image = QPixmap(int(w), int(h))
        self.ratio = 1
        self.loaded = False
        self.image.fill(Qt.white)
        self.w = w
        self.h = h

    def get_image(self, ratio):
        if self.ratio != ratio:
            res = self.image.scaledToWidth(int(self.w * ratio), QtCore.Qt.FastTransformation)
            return res
        else:
            return self.image

    def set_image(self, image, ratio):
        self.image = image
        self.ratio = ratio

    def get_orig_size(self):
        return self.w, self.h


class MuPDFRenderer(QLabel):

    # Signals
    document_changed = pyqtSignal()
    document_about_to_change = pyqtSignal()
    image_ready = pyqtSignal(int, float, int, QPixmap)
    sync_requested = pyqtSignal()
    page_updated = pyqtSignal(int)
    words_changed = pyqtSignal(int)

    # Constants
    OPEN_OK = 1
    OPEN_ERROR = 2
    OPEN_REQUIRES_PASSWORD = 3

    def __init__(self):
        super().__init__()
        self.filename = None
        self.images = []
        self.document = None
        self.mutex = []
        self.max_width = 0
        self.max_height = 0
        self.h = QThreadPool()
        self.h.setMaxThreadCount(100)
        self.blanks = {}

    def open_pdf(self, file, password=None):
        self.filename = file
        try:
            self.document = fitz.Document(file)
            if self.document.needs_pass:
                if password is None:
                    return self.OPEN_REQUIRES_PASSWORD
                else:
                    self.document.authenticate(password)

            # self.document = fitz.open(file, password=password)
            self.set_document(self.document, True)
            # print("Opened", self.document.metadata)
            return self.OPEN_OK

        except:
            traceback.print_exc()
            return self.OPEN_ERROR

    def get_page_size(self, index):
        return self.document[index].rect[2], self.document[index].rect[3]

    def set_image(self, index, image, ratio):
        self.images[index].set_image(image, ratio)
        self.images[index].loaded = True

    def get_num_of_pages(self):
        return len(self.document)

    def get_max_pages_size(self):
        return self.max_width, self.max_height

    def set_document(self, document, emit):
        self.document_about_to_change.emit()
        self.document = document
        self.images.clear()
        self.mutex.clear()
        self.max_width = 0
        self.max_height = 0

        for i in range(self.get_num_of_pages()):
            w, h = self.get_page_size(i)
            self.max_width = max(self.max_width, w)
            self.max_height = max(self.max_height, h)
            self.images.append(Image(w, h))
            self.mutex.append(QMutex())

        if emit:
            self.document_changed.emit()

    def request_image_by_width(self, index, width):
        w, h = self.get_page_size(index)
        ratio = width / w
        return self.request_image(index, ratio)

    def request_image(self, index, ratio, key=None):
        if not self.images[index].loaded or self.images[index].ratio != ratio:
            self.load(index, ratio, key)
            return self.get_image(index, ratio), False  # self.get_blank(index, ratio), False
        else:
            return self.images[index].get_image(ratio), True

    def get_image(self, index, ratio):
        return self.images[index].get_image(ratio)

    def get_blank(self, index, ratio):
        w, h = self.images[index].get_orig_size()

        if self.blanks.get(ratio) is None:
            self.blanks[ratio] = QPixmap(int(w * ratio), int(h * ratio))
            self.blanks[ratio].fill(Qt.white)

        return self.blanks[ratio]

    def load(self, index, ratio, key):
        class Loader(QRunnable):
            def __init__(self, renderer: MuPDFRenderer, index, ratio, key, mutex):
                super().__init__()
                self.renderer = renderer
                self.index = index
                self.ratio = ratio
                self.key = key

            def run(self):
                image = self.renderer.images[self.index]
                if image.ratio == self.ratio and image.loaded:
                    # print("As is ", self.index, self.key)
                    self.renderer.image_ready.emit(self.index, self.ratio, self.key, image.image)
                elif image.ratio > self.ratio and image.loaded:
                    # print("Scaling down ", self.index, self.key)
                    pixmap = image.image.scaledToWidth(int(image.w * ratio), QtCore.Qt.SmoothTransformation)
                    self.renderer.image_ready.emit(self.index, self.ratio, self.key, pixmap)
                else:
                    mat = fitz.Matrix(self.ratio, self.ratio)

                    pix = self.renderer.get_document()[self.index].get_pixmap(matrix=mat, alpha=False, annots=True)
                    image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

                    pixmap = QPixmap.fromImage(image)
                    self.renderer.set_image(index, pixmap, ratio)
                    self.renderer.image_ready.emit(self.index, self.ratio, self.key, pixmap)

        loader = Loader(self, index, ratio, key, self.mutex[index])
        self.h.start(loader)

    def get_document(self):
        return self.document

    def get_filename(self):
        return self.filename


