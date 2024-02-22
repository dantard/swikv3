import io
import math
import os
import random
import shutil
import time
import traceback
from os.path import exists
from shutil import move
from typing import List
import tempfile
import fitz
from PIL import Image
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QRunnable, QRect, QThread, QRectF, QPoint, QUrl, QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import QPixmap, QImage, QColor, QDesktopServices, QPainter, QBrush
from PyQt5.QtWidgets import QGraphicsRectItem, QApplication
from fitz import PDF_ENCRYPT_KEEP, PDF_WIDGET_TYPE_TEXT, PDF_WIDGET_TYPE_COMBOBOX, PDF_WIDGET_TYPE_CHECKBOX, \
    TEXTFLAGS_DICT, TEXT_PRESERVE_IMAGES, Rect, PDF_WIDGET_TYPE_RADIOBUTTON, TEXT_ENCODING_LATIN, get_text_length, TEXT_ALIGN_CENTER
from fitz.utils import delete_widget


docum = []


class MuPDFRenderer:
    class OpenResult:
        OK = 1
        ERROR = 2
        PASSWORD = 3

    ERROR = 0
    FALSE = 0
    OK = 1
    NEED_RELOAD = 2
    DOESNT_NEED_RELOAD = 3
    WORKAROUND = 4

    def replace_widgets(self, refresh=True):
        for i, p in enumerate(self.document):
            widgets = p.widgets()
            for w in widgets:  # type: fitz.Widget
                if w.field_type == PDF_WIDGET_TYPE_RADIOBUTTON:
                    continue
                widget = fitz.Widget()
                widget.rect = w.rect
                widget.field_type = w.field_type
                widget.field_name = w.field_name
                widget.field_value = w.field_value

                if w.field_type == PDF_WIDGET_TYPE_COMBOBOX:
                    widget.choice_values = w.choice_values

                delete_widget(p, w)
                p.add_widget(widget)
        if refresh:
            self.refresh()

    def replace_font(self, font, offset=0, refresh=True):
        for i, p in enumerate(self.document):
            tw = fitz.TextWriter(p.rect)
            data = p.get_text("dict", sort=False, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)
            blocks = data.get('blocks', [])
            for block in blocks:
                for line in block.get('lines', []):
                    for span in line.get("spans", []):
                        font = span['font']
                        if 'bold' in font.lower():
                            font = fitz.Font(fontname="hebo")
                        else:
                            font = fitz.Font(fontname="helv")
                        tw.append((span['bbox'][0], span['bbox'][3] + offset), span['text'], fontsize=span['size'], font=font)
                        p.add_redact_annot(span['bbox'], "", fill=(1, 1, 1))
            p.apply_redactions()
            tw.write_text(p)
        if refresh:
            self.refresh()

    def refresh(self):
        self.set_document(self.document, True)

    def mimic2(self):
        doc = fitz.open()
        for i, p in enumerate(self.document):
            doc.new_page()
            tw = fitz.TextWriter(doc[-1].rect)
            # boxes = p.get_text("words", sort=True, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)
            # for w in boxes:
            #    x1, y1, x2, y2, text, block_no, line_no, word_no = w
            #    tw.append((x1, y2), text, fontsize=10)
            page_fonts = self.get_fonts(i)
            data = p.get_text("dict", sort=False, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)
            blocks = data.get('blocks', [])
            tw = fitz.TextWriter(doc[-1].rect)
            for block in blocks:
                for line in block.get('lines', []):
                    for span in line.get("spans", []):
                        font = span['font']
                        tw.append((span['bbox'][0], span['bbox'][3]), span['text'], fontsize=span['size'])  # , font=fitz.Font(fontname=font))
                        # doc[-1].insert_text((span['bbox'][0], span['bbox'][3]), span['text'], fontsize=span['size'], fontname=font, color=(0,0,0))
            tw.write_text(doc[-1])

            for w in p.widgets():  # type: fitz.Widget
                widget = fitz.Widget()
                widget.rect = w.rect
                widget.field_type = w.field_type
                widget.field_name = w.field_name
                widget.field_value = w.field_value
                # if w.field_type == PDF_WIDGET_TYPE_TEXT or w.field_type == PDF_WIDGET_TYPE_CHECKBOX or w.field_type == PDF_WIDGET_TYPE_COMBOBOX:

                if w.field_type == PDF_WIDGET_TYPE_COMBOBOX:
                    widget.choice_values = w.choice_values

                doc[-1].add_widget(widget)
                print("adding widget", widget.field_name, widget.field_value, w.field_type)

            xreflen = self.document.xref_length()  # length of objects table
            for xref in range(1, xreflen):  # skip item 0!
                print("")
                print("object %i (stream: %s)" % (xref, doc.xref_is_stream(xref)))
                print(doc.xref_object(xref, compressed=False))

            page = p
            image_list = p.get_images(full=True)
            for image_index, img in enumerate(image_list, start=1):
                # get the XREF of the image
                xref = img[0]
                rect = p.get_image_bbox(img)

                # extract the image bytes
                base_image = self.document.extract_image(xref)
                image_bytes = base_image["image"]
                w, h = base_image["width"], base_image["height"]
                # get the image extension
                image_ext = base_image["ext"]
                doc[-1].insert_image(rect, pixmap=fitz.Pixmap(image_bytes))
                # load it to PIL
                image = Image.open(io.BytesIO(image_bytes))
                # save it to local disk
                image.save(open(f"image{1}_{1}.{image_ext}", "wb"))

        doc.save("mimic.pdf")
        self.set_document(doc, True)

    def get_images(self, index):
        images = list()

        p = self.document[index]
        image_list = p.get_images(full=True)
        for image_index, img in enumerate(image_list):
            # get the XREF of the image
            xref = img[0]
            rect = p.get_image_bbox(img)

            # extract the image bytes
            base_image = self.document.extract_image(xref)
            image_bytes = base_image["image"]
            w, h = base_image["width"], base_image["height"]
            # get the image extension
            image_ext = base_image["ext"]

            pix = fitz.Pixmap(image_bytes)
            # doc[-1].insert_image(rect, pixmap=fitz.Pixmap(image_bytes))
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            self.page_updated.emit(index)
            images.append((image, rect.x0, rect.y0, rect))

        #for _, _, _, rect in images:
        #    p.add_redact_annot(rect)  # cover top-left image with aredaction
        #    p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
        #    # p.delete_image(img[0])

        #self.refresh()
        return images

    def __init__(self):
        super().__init__()
        self.render_annots = True

    def set_render_annots(self, value):
        self.render_annots = value

    def open_pdf(self, file, password=None):
        super().open_pdf(file)
        try:
            self.document = fitz.Document(file)
            if self.document.needs_pass:
                if password is None:
                    return self.OpenResult.PASSWORD
                else:
                    self.document.authenticate(password)

            # self.document = fitz.open(file, password=password)
            self.set_document(self.document, True)
            # print("Opened", self.document.metadata)
            return self.OpenResult.OK

        except:
            traceback.print_exc()
            return self.OpenResult.ERROR

    def save(self, filename, reopen=True):

        # Delete annotations to avoid them to
        # be added every time the doc is saved
        for page in self.document:
            for a in page.annots():
                if a.type[0] == fitz.PDF_ANNOT_HIGHLIGHT or a.type[0] == fitz.PDF_ANNOT_SQUARE or a.type[0] == fitz.PDF_ANNOT_FREE_TEXT:
                    page.delete_annot(a)

        self.sync_requested.emit()

        try:
            if filename != self.get_filename():
                self.document.save(filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
                return MuPDFRenderer.NEED_RELOAD
            elif self.document.can_save_incrementally():
                self.document.save(filename, encryption=PDF_ENCRYPT_KEEP, incremental=True, deflate=True)
                return MuPDFRenderer.DOESNT_NEED_RELOAD
            else:
                tmp_dir = tempfile.gettempdir() + os.sep
                temp_filename = tmp_dir + "swik_{}.tmp".format(int(time.time()))

                self.document.save(temp_filename, encryption=PDF_ENCRYPT_KEEP, deflate=True, garbage=3)
                self.document.close()

                shutil.copy2(temp_filename, filename)

                if exists(temp_filename):
                    os.remove(temp_filename)
                return MuPDFRenderer.NEED_RELOAD

        except:
            traceback.print_exc()
            return MuPDFRenderer.ERROR

    def set_document(self, document, emit):
        super().set_document(document, emit)

    def get_links(self, index):
        self.annoting_page = self.document[index]

        links = list()
        pdf_link = self.annoting_page.first_link
        while pdf_link is not None:
            if QUrl(pdf_link.uri).isValid():
                link = Link(pdf_link, self.document.resolve_link(pdf_link.uri))
                # link.signals.clicked.connect(self.go_to_xref)
                links.append(link)
                pdf_link = pdf_link.next

        return links

    def get_annotations_fitz(self, index) -> List[fitz.Annot]:
        return self.document[index].annots()

    def get_annotations(self, index):
        annots = list()
        for a in self.document[index].annots():  # type: fitz.Annot

            if a.type[0] == fitz.PDF_ANNOT_SQUARE:
                a.set_rect(a.rect * self.document[index].rotation_matrix)
                annot = Annotation()
                annot.fromFitzAnnot(a)
                annots.append(annot)
                self.document[index].delete_annot(a)
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

        return annots

    def remove_widgets(self, index):
        for i, field in enumerate(self.document[index].widgets()):
            delete_widget(self.document[index], field)
            continue

    def create_widgets(self, index):
        pdf_widgets = list()
        radios = dict()
        for i, field in enumerate(self.document[index].widgets()):

            if field.field_type == PDF_WIDGET_TYPE_TEXT:
                rect = QRectF(field.rect[0], field.rect[1], field.rect[2] - field.rect[0],
                              field.rect[3] - field.rect[1])

                text_field = PdfWidgetTextField(field.field_name, rect, field.field_value, field.field_flags, field.text_fontsize)
                pdf_widgets.append(text_field)
                field.field_value = ""
                field.update()

            elif field.field_type == PDF_WIDGET_TYPE_COMBOBOX:
                rect = QRectF(field.rect[0], field.rect[1], field.rect[2] - field.rect[0],
                              field.rect[3] - field.rect[1])
                combo_field = PdfWidgetComboBox(field.field_name, rect, field.field_value, field.choice_values, i)
                pdf_widgets.append(combo_field)
                field.field_value = ""
                field.update()
            elif field.field_type == PDF_WIDGET_TYPE_CHECKBOX:
                rect = QRectF(field.rect[0], field.rect[1], field.rect[2] - field.rect[0],
                              field.rect[3] - field.rect[1])
                combo_field = PdfWidgetCheckBox(field.field_name, rect, field.field_value, i)
                pdf_widgets.append(combo_field)
                # field.field_value = 'Off'
                field.update()
            elif field.field_type == PDF_WIDGET_TYPE_RADIOBUTTON:
                if radios.get(field.field_name) is None:
                    radios[field.field_name] = 0
                # print("getting:", field.field_name, field.field_value, field.field_label, field.field_flags)

                rect = QRectF(field.rect[0], field.rect[1], field.rect[2] - field.rect[0],
                              field.rect[3] - field.rect[1])
                combo_field = PdfWidgetRadioButton(field.field_name, rect, field.field_value, radios[field.field_name])
                pdf_widgets.append(combo_field)
                # field.field_value = ""
                # field.update()
                radios[field.field_name] = radios[field.field_name] + 1

                '''
                print("reading", field.field_value)
                widget.fromRect(rect, 1, content=field.field_value)
                widget.name = field.field_name
                widget.flags = field.field_flags
                widgets.append(widget)

                field.field_value = ""

                

                if field.field_type == PDF_WIDGET_TYPE_CHECKBOX:
                    widget.set_type(Widget.CHECKBOX)

                field.update()
                '''
        return pdf_widgets

    def project(self, point, index):
        return point * self.document[index].derotation_matrix

    def get_rotation(self, index):
        return self.document[index].rotation

    def update_widget(self, pdf_widget, index):
        aindex = 0
        for i, field in enumerate(self.document[index].widgets()):
            # print("SETTING widget:", field.field_name, pdf_widget.get_value(), "index", pdf_widget.get_index(), field.field_flags)
            if field.field_name == pdf_widget.get_name():

                if field.field_type == PDF_WIDGET_TYPE_RADIOBUTTON:
                    if aindex == 2:
                        field.field_value = True
                        field.update()
                    else:
                        field.field_value = False
                        field.update()
                    aindex += 1
                    pass
                else:
                    field.field_value = pdf_widget.get_value()
                    field.update()
                break

    def insert_page(self, where, before):
        w, h = self.get_page_size(where)
        where = where if before else where + 1
        self.document.insert_page(where, width=w, height=h)
        self.set_document(self.document, True)

    def rotate_page(self, index, angle, update=False):
        self.document[index].set_rotation(self.document[index].rotation + angle)
        if update:
            self.set_document(self.document, True)

    def rotate(self, angle):
        for p in self.document:
            p.set_rotation(p.rotation + angle)
        self.set_document(self.document, True)

    def remove_watermark(self, index):
        affected = process_page(self.document[index])
        return affected

    def refresh(self):
        self.set_document(self.document, True)

    def adjust_crop(self, image: QImage) -> QRect:
        # Create a QColor object to represent white
        white = QColor(Qt.white)

        # Initialize variables for the dimensions of the smallest rectangle
        # that contains non-white pixels
        left = image.width()
        top = image.height()
        right = 0
        bottom = 0

        # Iterate over all pixels in the image
        for x in range(image.width()):
            for y in range(image.height()):
                # Get the color of the current pixel
                color = QColor(image.pixel(x, y))

                # If the color is not white, update the dimensions of the
                # smallest rectangle that contains non-white pixels
                if color != white:
                    left = min(left, x)
                    top = min(top, y)
                    right = max(right, x)
                    bottom = max(bottom, y)

        # Return the smallest rectangle that contains non-white pixels
        return QRect(left, top, right - left + 1, bottom - top + 1)

    def render_page_for_printing(self, index, dpi, rectangle=None):
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        # render page to an image
        if rectangle is None:
            pix = self.get_document()[index].get_pixmap(matrix=mat, alpha=False, annots=True)
        else:
            clip = fitz.Rect(rectangle.x(), rectangle.y(), rectangle.x() + rectangle.width(), rectangle.y() + rectangle.height())
            pix = self.get_document()[index].get_pixmap(matrix=mat, alpha=False, annots=True, clip=clip)
        # img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        # height, width, channel = img.shape
        # image = QImage(img.data, width, height, 3 * width, QImage.Format_RGB888)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        # image = image.scaledToWidth(300, Qt.SmoothTransformation)
        return QPixmap.fromImage(image)

    def export_pages(self, order, filename, open_after=False):
        doc = fitz.open()
        for i in order:
            doc.insert_pdf(self.document, from_page=i, to_page=i)
        doc.save(filename, encryption=PDF_ENCRYPT_KEEP)
        if open_after:
            self.open_pdf(filename)

    def append_pdf(self, filename):
        r = fitz.Rect(10, 10, 20, 20)
        for ii, p in enumerate(self.document):
            self.annoting_page = p
            fitz_annot = self.annoting_page.add_rect_annot(r)
            fitz_annot.set_info(None, "", "", None, None, "")
            fitz_annot.set_border(width=0)
            fitz_annot.set_colors(stroke=(1, 1, 1), fill=(1, 1, 1))
            fitz_annot.update(opacity=0)
            fitz_annot.set_name(
                "__swik_info_page_filename:" + str(ii + 1) + ":" + os.path.basename(self.get_filename()))

        doc2 = fitz.open(filename)
        for ii, p in enumerate(doc2):
            self.annoting_page = p
            fitz_annot = self.annoting_page.add_rect_annot(r)
            fitz_annot.set_info(None, os.path.basename(filename), "", None, None, "")
            fitz_annot.set_border(width=0)
            fitz_annot.set_colors(stroke=(1, 1, 1), fill=(1, 1, 1))
            fitz_annot.update(opacity=0)
            fitz_annot.set_name("__swik_info_page_filename:" + str(ii + 1) + ":" + os.path.basename(filename))

        self.document.insert_pdf(doc2)
        self.set_document(self.document, True)

    def do_rearrange_pages(self, order, emit):
        self.document.select(order)
        self.set_document(self.document, emit)

    def get_page_fonts(self, index):
        return self.document.get_page_fonts(index)

    def get_fonts(self, index):
        fonts = set()
        font_info = self.document.get_page_fonts(index)

        for font in font_info:
            # Add the font name to the set of fonts
            fonts.add((font[3], font[4]))

        for k, v in fitz.Base14_fontdict.items():
            fonts.add((v, v))

        return sorted(list(fonts))

    def get_page_size(self, index):
        # print("page", index, self.document[index].rotation, self.document[index].rect[2], self.document[index].rect[3])
        return self.document[index].rect[2], self.document[index].rect[3]

    def redo(self):
        self.document.journal_redo()
        self.refresh()

    def undo(self):
        self.document.journal_undo()
        self.refresh()

    def start_journal(self, name):
        if not self.document.journal_is_enabled():
            print("enabling")
            self.document.journal_enable()

        self.document.journal_start_op(name)
        print("entering ", name)

    def stop_journal(self):
        #self.document.journal_stop_op()
        print("done ")

    CROP_EMPTY_PAGE = -1
    CROP_OK = 0

    def set_cropbox(self, page, rect: QRect, ratio, add_page=False, adjust=False):
        self.kk.lock()

        self.start_journal("crop")
        image = self.render_page_for_printing(page, 72 * 2)

        x, y, w, h = int(rect.x() / ratio), int(rect.y() / ratio), int(rect.width() / ratio), int(rect.height() / ratio)
        cx, cy = self.document[page].cropbox.x0, self.document[page].cropbox.y0

        copy = image.copy(x * 2, y * 2, w * 2, h * 2).toImage()

        if adjust:
            q = self.adjust_crop(copy)
        else:
            q = copy.rect()

        if q.isEmpty():
            self.kk.unlock()
            return MuPDFRenderer.CROP_EMPTY_PAGE

        if add_page:
            self.document.fullcopy_page(page)
            page = -1

        self.document[page].set_cropbox(fitz.Rect(x + cx + q.x() / 2,
                                                  y + cy + q.y() / 2,
                                                  x + cx + q.x() / 2 + q.width() / 2,
                                                  y + cy + +q.y() / 2 + q.height() / 2) * self.document[
                                            page].derotation_matrix)
        #self.document[page].set_artbox(fitz.Rect(x + cx + q.x() / 2,
        #                                         y + cy + q.y() / 2,
        #                                         x + cx + q.x() / 2 + q.width() / 2,
        #                                         y + cy + +q.y() / 2 + q.height() / 2) * self.document[
        #                                   page].derotation_matrix)

        if not add_page:
            w, h = self.get_page_size(page)
            self.images[page].update(w, h)
            self.page_updated.emit(page)

        self.stop_journal()
        self.set_document(self.document, True)

        self.kk.unlock()
        return MuPDFRenderer.CROP_OK

    def get_num_of_pages(self):
        return len(self.document) if self.document else 0

    def load(self, index, ratio, key):
        # print("EV: LOAD")

        class Loader(QRunnable):
            def __init__(self, renderer: MuPDFRenderer, index, ratio, key, mutex):
                super().__init__()
                self.renderer = renderer
                self.index = index
                self.ratio = ratio
                self.key = key
                # self.mutex = mutex

            def run(self):
                # TODO: QThread.msleep(50 + random.randint(0, 250))
                image = self.renderer.images[self.index]
                if image.ratio == self.ratio and image.loaded:
                    # print("As is ", self.index, self.key)
                    self.renderer.image_ready.emit(self.index, self.ratio, self.key, image.image)
                elif image.ratio > self.ratio and image.loaded:
                    # print("Scaling down ", self.index, self.key)
                    pixmap = image.image.scaledToWidth(int(image.w * ratio), QtCore.Qt.SmoothTransformation)
                    self.renderer.image_ready.emit(self.index, self.ratio, self.key, pixmap)
                else:
                    # print("Belated load of page ", self.index, self.key, ratio)
                    # self.renderer.mutex[self.index].lock()
                    # ratio = ratio if ratio is not None else self.ratio
                    mat = fitz.Matrix(self.ratio, self.ratio)

                    if True:
                        pix = self.renderer.get_document()[self.index].get_pixmap(matrix=mat, alpha=False, annots=self.renderer.render_annots)
                        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                    else:
                        # render page to an image
                        pix = self.renderer.get_document()[self.index].get_pixmap(matrix=mat, alpha=False, annots=True)
                        image1 = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

                        pix = self.renderer.get_document()[self.index].get_pixmap(matrix=mat, alpha=False, annots=False)
                        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

                        for a in self.renderer.get_document()[self.index].annots():
                            portion = image1.copy(a.rect[0] * self.ratio, a.rect[1] * self.ratio, a.rect[2] * self.ratio - a.rect[0] * self.ratio,
                                                  a.rect[3] * self.ratio - a.rect[1] * self.ratio)
                            painter = QPainter(image)
                            painter.drawImage(a.rect[0] * self.ratio, a.rect[1] * self.ratio, portion)
                            painter.end()

                        for a in self.renderer.get_document()[self.index].widgets():
                            portion = image1.copy(a.rect[0] * self.ratio, a.rect[1] * self.ratio, a.rect[2] * self.ratio - a.rect[0] * self.ratio,
                                                  a.rect[3] * self.ratio - a.rect[1] * self.ratio)
                            painter = QPainter(image)
                            painter.drawImage(a.rect[0] * self.ratio, a.rect[1] * self.ratio, portion)
                            painter.end()

                    # img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    # height, width, channel = img.shape
                    # image = QImage(img.data, width, height, 3 * width, QImage.Format_RGB888)

                    pixmap = QPixmap.fromImage(image)
                    self.renderer.set_image(index, pixmap, ratio)
                    # self.renderer.mutex[self.index].unlock()
                    self.renderer.image_ready.emit(self.index, self.ratio, self.key, pixmap)
                    # print("Belated emitted")
                    # print("EV: IMAGE_READY (Renderer)")

        loader = Loader(self, index, ratio, key, self.mutex[index])
        # QThreadPool.globalInstance().setMaxThreadCount(1000)
        # QThreadPool.globalInstance().start(loader)
        self.h.start(loader)
        '''TODO:
        page = self.document[1]
        print(page.get_fonts())
        for rect in page.search_for("been"):
            page.add_redact_annot(rect, "Holssssa", fontname=page.get_fonts()[1][4])
        page.apply_redactions()
        '''

    def keep_inner_rect(self, doc, index, arect, set_cropbox=True):
        page_rect = QRectF(doc[index].rect[0], doc[index].rect[1], doc[index].rect[2] - doc[index].rect[0], doc[index].rect[3] - doc[index].rect[1])
        rects = get_non_overlapping(page_rect, arect)

        for rect in rects:
            r = fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
            doc[0].add_redact_annot(r, "", fill=(1, 1, 1))
        doc[index].apply_redactions()
        if set_cropbox:
            doc[index].set_cropbox(fitz.Rect(arect.x(), arect.y(), arect.x() + arect.width(), arect.y() + arect.height()))

    def replace_word(self, index, rect, new_word, fill=(1, 1, 1), font='Helvetica', fontsize=15, emit=True, color=(0, 0, 0)):
        self.kk.lock()

        # self.start_journal("replace_word")

        a = fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()) * self.document[
            index].derotation_matrix

        self.document[index].add_redact_annot(a, "", fill=fill, fontname=font, fontsize=fontsize)

        try:
            self.document[index].apply_redactions()
        except:
            traceback.print_exc()
            self.kk.unlock()
            return False
        rc, count = -1, 0
        while rc < 0 and count < 100:
            rc = self.document[index].insert_textbox(
                a,
                new_word,
                color=color,
                align=fitz.TEXT_ALIGN_LEFT,
                fontsize=fontsize,
                fontname=font,
                fill=color
            )
            a.x1, a.y1, count = a.x1 + 1, a.y1 + 1, count + 1
        # for debugging #self.document[index].draw_rect(a)

        self.images[index].loaded = False

        # self.stop_journal()
        self.kk.unlock()

        if emit:
            self.page_updated.emit(index)
            self.words_changed.emit(index)

    def add_widget(self, index, rect, text):
        form_field_rect = fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        widget = fitz.Widget()
        widget.rect = form_field_rect
        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        widget.field_name = "text_field_" + str(time.time_ns())
        widget.field_value = text
        self.document[index].add_widget(widget)
        self.images[index].loaded = False
        self.page_updated.emit(index)

    def encrypt(self, filename, password):
        self.document.save(filename, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password[0], user_pw=password[1])



    def get_page_orientation(self, index):
        return self.document[index].rotation

    def fix_page_orientation(self, orientation):
        doc = fitz.open()  # new output file
        for src_page in self.document:  # iterate over input pages
            src_rect = src_page.rect  # source page rect
            w, h = src_rect.br  # save its width, height
            src_rot = src_page.rotation  # save source rotation
            # src_page.set_rotation(orientation)  # set rotation to 0 temporarily
            '''
            page = doc.new_page(width=w, height=h)  # make output page
            page.show_pdf_page(  # insert source page
                page.rect,
                self.document,
                src_page.number,
                rotate=-src_rot,  # insert source page in orig. rotation
            )
            '''
            doc.insert_pdf(
                self.document,
                src_page.number,
                # rotate=-src_rot,  # insert source page in orig. rotation
            )
        self.set_document(doc, True)

    def get_words(self, index):
        # TODO: FUCKING PROBLEM with selection
        data = self.document[index].get_text("words", sort=False, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)
        return self.prepare_words(index, data)

    def prepare_words(self, index, boxes):
        word_objs = list()
        print("prepare_words", len(boxes), index)
        for w in boxes:
            x1, y1, x2, y2, text, block_no, line_no, word_no = w

            # Compute rectangle taking into account orientation
            ftzrect = fitz.Rect(x1, y1, x2, y2) * self.document[index].rotation_matrix
            rect = QRectF(ftzrect.x0, ftzrect.y0, ftzrect.x1 - ftzrect.x0, ftzrect.y1 - ftzrect.y0)

            word = Word(rect, text, line_no, block_no, index)
            word_objs.append(word)

        return word_objs

    def get_word_font(self, word):
        print("words page", word.page)
        data = self.document[word.page].get_text("dict", sort=False, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)
        if data is not None:
            blocks = data.get('blocks', [])
            # print(blocks)
            if len(blocks) > word.block:
                lines = blocks[word.block]
                if lines is not None:
                    lines = lines.get('lines', [])
                    if len(lines) > word.line_no:
                        line = lines[word.line_no]
                        #print(line)
                        for span in line.get("spans", []):
                            #print(span)
                            x1, y1, x2, y2 = span["bbox"]
                            rect2 = QRectF(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                            #rect = QRectF(word.pos().x(), word.pos().y(), word.rect().width(), word.rect().height())
                            pr = word.get_page_rect()
                            rect = QRectF(pr.x(), pr.y(), pr.width(), pr.height())
                            if rect2.intersected(rect):
                                h = span.get("color")
                                b = h & 255
                                g = (h >> 8) & 255
                                r = (h >> 16) & 255
                                print(span, "kkjslkdjs", r, g, b)
                                word.set_font(span.get('font'), span.get('size'), (r / 255, g / 255, b / 255))
                                return True
        return False

    def search_for(self, needle):
        boxes = list()
        for i, page in enumerate(self.document):  # type: fitz.Page
            for b in page.search_for(needle):
                boxes.append((QRectF(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0), i, page.get_textbox(b)))
        return boxes

    def import_as_pdf(self, filename):
        xps = fitz.open(filename)
        pdfbytes = xps.convert_to_pdf()
        pdf = fitz.open("pdf", pdfbytes)
        filename += ".pdf"
        pdf.save(filename)
        self.open_pdf(filename)

    def insert_image(self, index, rect, filename, keep_proportion=False):

        rect = fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())

        if filename[-3:] == "pdf":
            xps = fitz.open(filename)
            self.document[index].show_pdf_page(rect, xps, rotate=-xps[0].rotation)
            xps.close()

        else:
            self.document[index].insert_image(rect, filename=filename, keep_proportion=keep_proportion)
        # self.set_document(self.document, True)

    '''
        def insert_qimage(self, index, rect, qimage):
        rect = fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        tempdir = tempfile.gettempdir() + os.sep
        filename = tempdir + "swik_img_{}.png".format(int(time.time()))
        qimage.save(filename)
        self.document[index].insert_image(rect, filename=filename)
        os.remove(filename)
    '''

    def insert_qimage(self, index, rect, qimage):
        rect = fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        qimage.save(buffer, "PNG")

        # Create a fitz.Pixmap from the bytes
        pixmap = fitz.Pixmap(byte_array.data())
        self.document[index].insert_image(rect, pixmap=pixmap)

    def show_pdf(self, index, rect, xps, keep_proportion=False):
        rect = fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        self.document[index].show_pdf_page(rect, xps)

    def get_metadata(self):
        return self.document.metadata

    def set_metadata(self, metadata):
        self.document.set_metadata(metadata)

    def close_file(self):
        self.document.close()

    def duplicate_page(self, indices, add_to_end=False):
        if add_to_end:
            # Just add the pages to the end
            for i in reversed(indices):
                self.document.fullcopy_page(i)
        else:
            num_pages = self.get_num_of_pages()

            # Add Pages to the end in reverse order
            for i in reversed(indices):
                self.document.fullcopy_page(i)

            # Put the pages in the right position
            # from the end to the beginning
            for i, dest_page in enumerate(reversed(indices)):
                page_num = num_pages + i
                self.document.move_page(page_num, dest_page)

        self.set_document(self.document, True)


def extract_text_process(filename, index, needles):
    docum = fitz.open(filename)
    boxes = docum[index].get_text("words", sort=False, flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES)
    docum.close()

    return index, boxes, needles
