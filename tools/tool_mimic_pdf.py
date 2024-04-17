import sys

from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QTreeWidget, QTreeWidgetItem, QComboBox, QHBoxLayout, QVBoxLayout, QPushButton, QWidget

from progressing import Progressing
from swiktext import SwikText
from tools.replace_fonts.repl_font import repl_font
from tools.replace_fonts.repl_fontnames import repl_fontnames
from tools.tool import Tool


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
                page = self.view.pages[i]
                for span in spans:
                    font = self.font_manager.get_font_info_from_nickname(span.font)
                    self.renderer.add_redact_annot(page.index, span.rect, Qt.white, minimize=True, apply=False)
                    if font is None:
                        font = self.font_manager.get_font_info_from_nickname("helv")
                        color = QColor(255, 0, 0)
                    else:
                        color = QColor(0, 0, 0)

                    swik_text = SwikText(span.text, page, self.font_manager,font["path"], span.size * 0.75)
                    midpoint = self.rectangle_midpoint(span.rect)
                    top_left = self.top_left_corner(midpoint, swik_text.boundingRect().width(), swik_text.boundingRect().height())
                    swik_text.setToolTip(font["nickname"])
                    swik_text.setPos(top_left)# + QPointF(span.size*0.01, 0))
                    swik_text.setDefaultTextColor(color)
                self.view.pages[i].invalidate()
                self.renderer.apply_redactions(i)

            self.finished.emit()

        self.progressing.start(process)


