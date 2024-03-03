import os
import shutil
import tempfile
import time
import traceback
from os.path import exists

import fitz
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QMutex, QRectF, QRect
from PyQt5.QtGui import QPixmap, QImage, QBrush, QPen, QColor
from PyQt5.QtWidgets import QLabel
from fitz import TEXTFLAGS_DICT, TEXT_PRESERVE_IMAGES, Font
from fitz import PDF_ENCRYPT_KEEP, PDF_ANNOT_SQUARE, PDF_ANNOT_IS_LOCKED

import utils
from annotations.highlight_annotation import HighlightAnnotation
from annotations.squareannotation import SquareAnnotation
from swiktext import SwikText
from utils import fitz_rect_to_qrectf
from word import Word, MetaWord


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


def convert_box_to_upside_down(filename, index, rect):
    # The signing is not done using PyMuPDF, so we need to compute
    # the square in the pyhanko page (which to make everything
    # more complicated uses upside-down coordinates (notice dy))
    # We need to get some info from the file that is about to be signed
    # that can be different from the one we are seeing (e.g. flatten + sign)

    # Open the doc to sign
    doc_to_sign = fitz.open(filename)

    # The projection is necessary to take into account orientation
    # rot = self.renderer.get_rotation(page.index)
    rot = doc_to_sign[index].rotation

    # Get page size
    # w, h = self.renderer.get_page_size(page.index)
    w, h = doc_to_sign[index].rect[2], doc_to_sign[index].rect[3]

    # Get derotation matrix
    derot_matrix = doc_to_sign[index].derotation_matrix

    # Close the file, it is not needed anymore
    doc_to_sign.close()

    # Take into account that pyhanko uses upside-down coordinates
    dy = w if rot == 90 or rot == 270 else h

    # Rotate according to the orientation and create thw box
    # r1 = self.renderer.project(fitz.Point(rect.x(), rect.y()), page.index)
    r1 = fitz.Point(rect.x(), rect.y()) * derot_matrix
    box = (r1.x,
           dy - r1.y,
           r1.x + rect.width(),
           dy - (r1.y + rect.height())
           )
    return box


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
            print("Opened", self.document.metadata)
            return self.OPEN_OK

        except:
            traceback.print_exc()
            return self.OPEN_ERROR

    def save_pdf(self, filename):
        self.sync_requested.emit()

        if filename != self.get_filename():
            self.document.save(filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
            self.set_document(self.document, True)
            return 0
        elif self.document.can_save_incrementally():
            self.document.save(filename, encryption=PDF_ENCRYPT_KEEP, incremental=True, deflate=True)
            self.set_document(self.document, True)
            return 1
        else:
            tmp_dir = tempfile.gettempdir() + os.sep
            temp_filename = tmp_dir + "swik_{}.tmp".format(int(time.time()))

            self.document.save(temp_filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
            self.document.close()

            shutil.copy2(temp_filename, filename)

            if exists(temp_filename):
                os.remove(temp_filename)
            self.open_pdf(filename)
            return 2

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

    def request_image(self, index, ratio, key=None, force=False):
        if not self.images[index].loaded or self.images[index].ratio != ratio or force:
            self.load(index, ratio, key, force)
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

    def load(self, index, ratio, key, force):
        class Loader(QRunnable):
            def __init__(self, renderer: MuPDFRenderer, index, ratio, key, mutex):
                super().__init__()
                self.renderer = renderer
                self.index = index
                self.ratio = ratio
                self.key = key
                self.force = force

            def run(self):
                image = self.renderer.images[self.index]
                if image.ratio == self.ratio and image.loaded and not self.force:
                    # print("As is ", self.index, self.key)
                    self.renderer.image_ready.emit(self.index, self.ratio, self.key, image.image)
                elif image.ratio > self.ratio and image.loaded and not self.force:
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

    def extract_words(self, page_id):
        boxes = self.document[page_id].get_text("words", sort=True, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)

        word_objs = list()

        for i, w in enumerate(boxes):
            x1, y1, x2, y2, text, block_no, line_no, word_no = w

            # Compute rectangle taking into account orientation
            fitz_rect = fitz.Rect(x1, y1, x2, y2) * self.document[page_id].rotation_matrix
            rect = fitz_rect_to_qrectf(fitz_rect)

            word = Word(page_id, i, text, rect, word_no=word_no, line_no=line_no, block_no=block_no)
            word_objs.append(word)

        return word_objs

    def rearrange_pages(self, order, emit):
        self.document.select(order)
        # self.set_document(self.document, emit)

    def set_cropbox(self, page, rect: QRect, ratio, absolute=False):

        x, y, w, h = int(rect.x() / ratio), int(rect.y() / ratio), int(rect.width() / ratio), int(rect.height() / ratio)

        if not absolute:
            # in this case the square is relative to the current cropbox
            cx, cy = self.document[page].cropbox.x0, self.document[page].cropbox.y0
        else:
            cx, cy = 0, 0

        print(x, y, w, h, cx, cy, "cropbox")

        self.document[page].set_cropbox(fitz.Rect(x + cx,
                                                  y + cy,
                                                  x + cx + w,
                                                  y + cy + h) * self.document[
                                            page].derotation_matrix)

        w, h = self.get_page_size(page)
        self.images[page].update(w, h)
        self.page_updated.emit(page)

        return True

    def get_cropbox(self, page):
        x0, y0 = self.document[page].cropbox.x0, self.document[page].cropbox.y0
        x1, y1 = self.document[page].cropbox.x1, self.document[page].cropbox.y1
        return QRectF(x0, y0, x1 - x0, y1 - y0)

    def add_redact_annot(self, index, rect, color):
        print("applying", index, rect, color)
        page = self.document[index]
        rect = utils.qrectf_to_fitz_rect(rect)
        color = utils.qcolor_to_fitz_color(color)
        page.add_redact_annot(rect, "", fill=color)
        page.apply_redactions()

    annoting =None
    def add_highlight_annot(self, index, annot):
        annoting = self.document[index]
        quads = []
        for r in annot.get_quads():  # type: QRectF
            q = fitz.Quad((r.x(), r.y()),
                          (r.x() + r.width(), r.y()),
                          (r.x(), r.y() + r.height()),
                          (r.x() + r.width(), r.y() + r.height()))
            quads.append(q)
        fitz_annot: fitz.Annot = annoting.add_highlight_annot(quads=quads)
#        fitz_annot.set_info(None, annot.content, "", None, None, "")
        # print("stroke", annot.stroke_from_qcolor(annot.brush().color()))
        stroke = utils.qcolor_to_fitz_color(annot.brush().color())
        fitz_annot.set_colors(stroke=stroke)
        fitz_annot.set_opacity(annot.opacity() if stroke is not None else 0.0)
#        fitz_annot.update()


    def get_annotations(self, page):
        annots = list()
        print("get annotatioons")
        for annot in self.document[page.index].annots():  # type: fitz.Annot
            print("one")
            if annot.type[0] == PDF_ANNOT_SQUARE:
                print("two", annot.colors)
                opacity = annot.opacity if 1 > annot.opacity > 0 else 0.999
                stroke = utils.fitz_color_to_qcolor(annot.colors['stroke'], opacity) if annot.colors['stroke'] is not None else Qt.transparent
                fill = utils.fitz_color_to_qcolor(annot.colors['fill'], opacity) if annot.colors['fill'] is not None else Qt.transparent
                border_width = annot.border['width']
                pen = QPen(stroke, border_width)

                swik_annot = SquareAnnotation(page, brush=fill, pen=pen)

                annot.set_rect(annot.rect * self.document[page.index].rotation_matrix)

                swik_annot.setRect(QRectF(0, 0, annot.rect[2] - annot.rect[0], annot.rect[3] - annot.rect[1]))
                swik_annot.set_content(annot.info["content"])
                swik_annot.setToolTip(swik_annot.get_content())
                locked = annot.flags & PDF_ANNOT_IS_LOCKED
                swik_annot.set_movable(not locked)
                swik_annot.setPos(annot.rect[0], annot.rect[1])
                annots.append(swik_annot)
                self.document[page.index].delete_annot(annot)
            elif annot.type[0] == fitz.PDF_ANNOT_HIGHLIGHT:
                swik_annot = HighlightAnnotation(QColor(255, 0, 0, 80), page)
                swik_annot.setRect(QRectF(0, 0, annot.rect[2] - annot.rect[0], annot.rect[3] - annot.rect[1]))
                swik_annot.setPos(annot.rect[0], annot.rect[1])
                points = annot.vertices
                if points is not None:
                    quad_count = int(len(points) / 4)
                    for i in range(quad_count):
                        rect = fitz.Quad(points[i * 4: i * 4 + 4]).rect
                        rect = rect * self.document[page.index].rotation_matrix
                        quad = utils.fitz_rect_to_qrectf(rect)
                        swik_annot.add_quad(quad)
                self.document[page.index].delete_annot(annot)
                annots.append(swik_annot)

            '''
            elif a.type[0] == fitz.PDF_ANNOT_HIGHLIGHT:
                annot = HighlightAnnotation()
                annot.fromHighlight(a, self.document[index])
                # print("--------------->", a.colors["stroke"], a.opacity)
                annot.setBrush(utils.qcolor_from_stroke(a.colors["stroke"]))
                annot.setOpacity(a.opacity)
                annots.append(annot)
                self.document[index].delete_annot(a)
            elif a.type[0] == fitz.PDF_ANNOT_FREE_TEXT:
                a.set_rect(a.rect * self.document[index].rotation_matrix)
                annot = FreeTextAnnot()
                # print(self.document.xref_object(a.xref))
                annot.fromFitzAnnot(a)
                fields = self.document.xref_get_key(a.xref, "DA")[1].strip().split(" ")

                r, g, b = 0, 0, 0
                font, font_size = "/Helv", 11
                for i, f in enumerate(fields):
                    if f == "rg":
                        r, g, b = float(fields[i - 3]), float(fields[i - 2]), float(fields[i - 1])
                    elif f == "g":
                        r, g, b = float(fields[i - 1]), float(fields[i - 1]), float(fields[i - 1])
                    elif f == "Tf":
                        font = fields[i - 2]
                        font_size = float(fields[i - 1])

                pen = annot.pen()
                pen.setColor(QColor(Qt.transparent))
                annot.setPen(pen)
                annot.set_font(font, font_size, QColor(int(r * 255), int(g * 255), int(b * 255)))
                annot.set_border_color(QColor(int(r * 255), int(g * 255), int(b * 255)))

                annots.append(annot)
                self.document[index].delete_annot(a)
            '''
        return annots

    def add_annot(self, index, annot):
        if type(annot) == SquareAnnotation:
            print("adding", index, annot.rect(), annot.pos())
            page = self.document[index]
            fitz_rect = utils.qrectf_and_pos_to_fitz_rect(annot.rect(), annot.pos())
            pen: QPen = annot.pen()
            brush: QBrush = annot.brush()
            fitz_annot = page.add_rect_annot(fitz_rect)  # 'Square'
            fitz_annot.set_border(width=pen.width())
            fitz_annot.set_colors(stroke=utils.qcolor_to_fitz_color(pen.color()), fill=utils.qcolor_to_fitz_color(brush.color()))
            opacity = min(brush.color().alpha() / 255, 0.999)
            fitz_annot.set_opacity(opacity)
            fitz_annot.set_info(None, annot.get_content(), "", "", "", "")
            fitz_annot.update()

    def add_text(self, index, item: SwikText):
        color = utils.qcolor_to_fitz_color(item.defaultTextColor())
        tw = fitz.TextWriter(self.document[index].rect, color=color)
        x, y, h = item.pos().x(), item.pos().y(), item.sceneBoundingRect().height()
        font = Font(fontfile=item.get_ttf_filename())

        # tw.append((x,y + h), item.get_text(), font=font, fontsize=item.font().pointSizeF()*1.32)
        rect = utils.qrectf_and_pos_to_fitz_rect(item.get_rect_on_parent(), item.pos())
        rect.x1 = rect.x1 + 100
        rect.y0 += item.font().pointSize() / 3.5
        rect.y1 += item.font().pointSize() / 3.5
        tw.fill_textbox(rect, item.get_text(), font=font, fontsize=item.font().pointSizeF() * 1.325)
        tw.write_text(self.document[index])
