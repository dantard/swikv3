import sys
import time

from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QTreeWidget, QTreeWidgetItem, QComboBox, QHBoxLayout, QVBoxLayout, \
    QPushButton, QWidget, QGraphicsLineItem
from pymupdf import Rect, Point

import font_manager
from annotations.redactannotation import RedactAnnotation
from dialogs import FontAndColorDialog, ComposableDialog
from page import Page
from progressing import Progressing
from span import Span
from swiktext import SwikText
from tools.replace_fonts.repl_font import repl_font
from tools.replace_fonts.repl_fontnames import repl_fontnames
from tools.tool import Tool
from utils import fitz_rect_to_qrectf


class ToolMimicPDF(Tool):
    file_generate = pyqtSignal(str, int, float)

    def __init__(self, view, icon, parent, **kwargs):
        super(ToolMimicPDF, self).__init__(view, icon, parent, **kwargs)
        self.placeholder = None
        self.font_manager = kwargs.get('font_manager')
        self.widget = kwargs.get('widget')
        self.squares = []
        self.app = None
        self.texts = []
        self.helper = None
        self.tree = None

    def top_left_corner(self, midpoint, width, height):
        # Calculate the x-coordinate of the top-left corner
        top_left_x = midpoint.x() - (width / 2)

        # Calculate the y-coordinate of the top-left corner
        top_left_y = midpoint.y() - (height / 2)

        # Return the top-left corner as a QPointF
        return QPointF(top_left_x, top_left_y)

    def rectangle_midpoint(self, rect):
        # Midpoint of diagonal connecting top-left and bottom-right corners
        mid1 = QPointF(rect.topLeft() + rect.bottomRight()) / 2

        # Midpoint of diagonal connecting top-right and bottom-left corners
        mid2 = QPointF(rect.topRight() + rect.bottomLeft()) / 2

        # Midpoint of the rectangle
        midpoint = (mid1 + mid2) / 2

        return midpoint

    def init(self):
        self.texts.clear()
        self.squares.clear()

        self.helper = QWidget()
        self.helper.setContentsMargins(0, 0, 0, 0)
        self.helper.setLayout(QVBoxLayout())
        self.helper.layout().setAlignment(Qt.AlignTop)
        self.helper.layout().setContentsMargins(0, 0, 0, 0)
        generate_btn = QPushButton("Generate")
        apply_btn = QPushButton("Apply")
        colorize_btn = QPushButton("Colorize")
        colorize_btn.clicked.connect(self.colorize)
        colorize_btn.setCheckable(True)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Font", "Replace"])
        self.helper.layout().addWidget(self.tree)
        self.helper.layout().addWidget(colorize_btn)
        self.helper.layout().addWidget(generate_btn)
        self.helper.layout().addWidget(apply_btn)

        generate_btn.clicked.connect(self.generate)
        apply_btn.clicked.connect(self.apply)
        self.widget.set_app_widget(self.helper, title="Mimic PDF")
        fonts = set()
        for i in range(0, self.view.get_page_count()):
            spans = self.renderer.extract_spans(i)
            for span in spans:
                fonts.add(span.font)

        for font_name in fonts:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, font_name)
            child1 = QTreeWidgetItem(item)
            child1.setText(0, "New font")
            q = QPushButton(font_name)

            def chose_font(font, button):
                font_dialog = FontAndColorDialog(self.font_manager, font, 10, Qt.black)
                if font_dialog.exec() == ComposableDialog.Accepted:
                    button.setText(font_dialog.get_font().nickname)

            q.clicked.connect(lambda x=font_name, y=font_name, z=q: chose_font(y, z))
            self.tree.setItemWidget(child1, 1, q)

    def apply(self):
        self.renderer.sync_requested.emit()
        self.view.pages[0].invalidate()
        filename = self.renderer.get_filename().replace(".pdf", "-mimic.pdf")
        self.renderer.save_elsewhere(filename)
        self.widget.open_requested.emit(filename, self.view.page, self.view.get_ratio())

    def colorize(self):
        colors = [Qt.red, Qt.green, Qt.blue, Qt.yellow, Qt.magenta, Qt.cyan, Qt.darkRed, Qt.darkGreen,
                  Qt.darkBlue, Qt.darkYellow, Qt.darkMagenta, Qt.darkCyan, Qt.gray, Qt.darkGray, Qt.lightGray]

        if self.sender().isChecked():

            fonts = list()
            self.placeholder = Progressing(self.view, self.view.get_page_count(), "Analyzing PDF", cancel=True)

            def process():
                for i in range(0, self.view.get_page_count()):
                    if not self.placeholder.set_progress(i):
                        break
                    spans = self.renderer.extract_spans(i)
                    page = self.view.pages[i]
                    for span in spans:
                        a = QGraphicsRectItem(span.rect, page)
                        a.setToolTip(span.font)
                        self.squares.append(a)
                        if not span.font in fonts:
                            fonts.append(span.font)
                        index = fonts.index(span.font)
                        color = QColor(colors[index % len(colors)])
                        color.setAlphaF(0.5)
                        a.setBrush(color)
                self.placeholder.set_progress(self.view.get_page_count())

            self.placeholder.start(process)
        else:
            for i in self.squares:
                self.view.scene().removeItem(i)
            self.squares.clear()

    def generate(self):
        translate = {}

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            orig_font_name = item.text(0)
            new_font_name = self.tree.itemWidget(item.child(0), 1).text()
            translate[orig_font_name] = new_font_name

        print(translate)

        for i in self.texts:
            self.view.scene().removeItem(i)
        self.texts.clear()

        self.progressing = Progressing(self.view, self.view.get_page_count(), "Generating PDF", cancel=True)

        def process():
            for i in range(0, self.view.get_page_count()):
                if not self.progressing.set_progress(i):
                    break
                page: Page = self.view.pages[i]

                page.gather_words()
                '''
                for word in page.get_words():
                    font, size, color = self.renderer.get_word_font_info(word)
                    span = Span()
                    span.font = font
                    span.size = size
                    span.color = color
                    span.text = word.get_text()
                    span.rect = QRectF(word.pos().x(), word.pos().y(), word.rect().width(), word.rect().height())
                    span.ascender = 0
                    span.descender = 0
                '''

                spans = self.renderer.extract_spans(i)
                for span in spans:

                    new_font_name = translate.get(span.font)
                    font = self.font_manager.filter(nickname=new_font_name, pos=0)
                    # redact = RedactAnnotation(page, brush=Qt.white, pen=Qt.transparent)
                    # redact.setRect(span.rect)

                    # self.renderer.add_redact_annot(page.index, span.rect, minimize=True, apply=False)
                    if font is None or font.supported is False:
                        font = self.font_manager.filter(nickname='helv', pos=0)
                        color = QColor(255, 0, 0)
                    else:
                        color = span.color
                        color = QColor(255, 0, 0)

                    swik_text = SwikText(span.text, page, self.font_manager, font, span.size * 72.0 / 96.0)
                    self.texts.append(swik_text)

                    swik_text.setToolTip(font.full_name)
                    swik_text.setPos(span.rect.topLeft())

                    swik_text.setPos(swik_text.pos().x(),
                                     swik_text.pos().y() - (span.ascender + span.descender) * 72.0 / 96.0)
                    swik_text.setDefaultTextColor(color)
                try:
                    self.renderer.apply_redactions(i)
                except:
                    pass

                self.view.pages[i].invalidate()
            self.progressing.setValue(self.view.get_page_count())

        self.progressing.start(process)

    def finish(self):

        self.widget.remove_app_widget(self.helper)
        self.helper.deleteLater()
