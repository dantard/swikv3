import sys

from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QTreeWidget, QTreeWidgetItem, QComboBox, QHBoxLayout, QVBoxLayout, QPushButton, QWidget, QGraphicsLineItem
from pymupdf import Rect, Point

import font_manager
from progressing import Progressing
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
        self.layout = kwargs.get('layout')
        self.squares = []

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
        self.progressing = Progressing(self.view, self.view.get_page_count(), "Generating PDF", cancel=True)

        def process():
            for i in range(0, self.view.get_page_count()):
                if not self.progressing.set_progress(i):
                    break

                spans = self.renderer.extract_spans(i)

                # a = self.renderer.document[i].get_drawings()
                # for j in a:
                #     print(j)
                #     items = j["items"]
                #     for item in items:
                #         if item[0] == "re":
                #             re:Rect = item[1]
                #             rect = fitz_rect_to_qrectf(re)
                #             pp = QGraphicsRectItem(self.view.pages[i])
                #             pp.setRect(QRectF(0, 0, rect.width(), rect.height()))
                #             pp.setPos(rect.topLeft())
                #             pp.setBrush(Qt.cyan)
                #         elif item[0] == "l":
                #             p1:Point = item[1]
                #             p2:Point = item[2]
                #             pp = QGraphicsLineItem(self.view.pages[i])
                #             pp.setPen(Qt.magenta)
                #             pp.setLine(p1.x, p1.y, p2.x, p2.y)


                page = self.view.pages[i]
                for span in spans:
                    font = self.font_manager.filter(nickname=span.font, pos=0)
                    #self.renderer.add_redact_annot(page.index, span.rect, minimize=True, apply=False)
                    if font is None or font.supported is False:
                        font = self.font_manager.filter(nickname='helv', pos=0)
                        color = QColor(255, 0, 0)
                    else:
                        color = span.color

                    swik_text = SwikText(span.text, page, self.font_manager, font, span.size * 0.75)
                    midpoint = self.rectangle_midpoint(span.rect)
                    top_left = self.top_left_corner(midpoint, swik_text.boundingRect().width(), swik_text.boundingRect().height())
                    swik_text.setToolTip(font.full_name)
                    ### swik_text.setPos(top_left)  # + QPointF(span.size*0.01, 0))
                    swik_text.setPos(span.rect.topLeft() - QPointF(span.size*0.15, span.size*0.15))
                    swik_text.setDefaultTextColor(color)
                try:
                    self.renderer.apply_redactions(i)
                except:
                    pass

                self.view.pages[i].invalidate()

            self.emit_finished()

        self.progressing.start(process)
