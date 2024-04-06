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
        for i in range(0, self.view.get_page_count()):
            spans = self.renderer.extract_spans(i)
            page = self.view.pages[i]
            for span in spans:
                font = self.font_manager.get_font_info_from_nickname(span.font)
                # self.renderer.add_redact_annot(page.index, span.rect, Qt.white, True)
                if font is not None:
                    midpoint = self.rectangle_midpoint(span.rect)
                    a = SwikText(span.text, page, self.font_manager, font["path"], span.size * 0.75)

                    top_left = self.top_left_corner(midpoint, a.boundingRect().width(), a.boundingRect().height())

                    a.setPos(top_left)
                    self.view.pages[i].invalidate()

    def create_dialog(self, data):
        v_layout = QVBoxLayout()
        # layout.addLayout(v_layout)

        self.treeWidget = QTreeWidget()
        self.treeWidget.setHeaderLabels(["Items"])
        self.treeWidget.setColumnCount(1)
        #        self.treeWidget.itemExpanded.connect(self.resize_columns)
        for value in data:
            item = QTreeWidgetItem()

            old_fonts = str()
            for old_font in value.get("oldfont"):
                old_fonts += old_font + ", "
            old_fonts = old_fonts[:-2]
            item.setText(0, old_fonts)
            item.setToolTip(0, old_fonts)

            item2 = QTreeWidgetItem()
            item2.setText(0, value.get("info"))
            item2.setToolTip(0, value.get("info"))
            item.addChild(item2)

            combobox = QComboBox()
            combobox.addItem("Keep")
            combobox.currentTextChanged.connect(self.selected)
            combobox.item = item
            for font in self.font_manager.get_all_available_fonts():
                combobox.addItem(font.get("full_name"))

            item3 = QTreeWidgetItem()
            item.addChild(item3)

            self.treeWidget.invisibleRootItem().addChild(item)
            self.treeWidget.setItemWidget(item3, 0, combobox)
            self.treeWidget.setMaximumWidth(200)

        pb = QPushButton("Replace Fonts")
        pb.clicked.connect(self.do_replace)
        v_layout.addWidget(self.treeWidget)
        v_layout.addWidget(pb)
        self.helper = QWidget()
        self.helper.setLayout(v_layout)
        self.helper.setMaximumWidth(200)
        self.layout.insertWidget(0, self.helper)

#    def finish(self):
#        for square in self.squares:
#            self.view.scene().removeItem(square)
#        self.squares.clear()
#        self.layout: QHBoxLayout
#        self.layout.removeWidget(self.helper)
#        self.helper.deleteLater()
