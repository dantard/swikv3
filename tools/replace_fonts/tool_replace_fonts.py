from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QTreeWidget, QTreeWidgetItem, QComboBox, QHBoxLayout, QVBoxLayout, \
    QPushButton, QWidget

from progressing import Progressing
from swiktext import SwikText
from tools.replace_fonts.repl_font import repl_font
from tools.replace_fonts.repl_fontnames import repl_fontnames
from tools.tool import Tool


class ToolReplaceFonts(Tool):
    file_generate = pyqtSignal(str, int, float)

    def __init__(self, view, icon, parent, **kwargs):
        super(ToolReplaceFonts, self).__init__(view, icon, parent, **kwargs)
        self.placeholder = None
        self.font_manager = kwargs.get('font_manager')
        self.layout = kwargs.get('widget')
        self.squares = []
        self.treeWidget = None

    def init(self):
        v_layout = QVBoxLayout()
        # layout.addLayout(v_layout)

        self.treeWidget = QTreeWidget()
        self.treeWidget.setHeaderLabels(["Items"])
        self.treeWidget.setColumnCount(1)
        pb = QPushButton("Replace Fonts")
        pb.clicked.connect(self.replace_clicked)
        v_layout.addWidget(self.treeWidget)
        v_layout.addWidget(pb)
        self.helper = QWidget()
        self.helper.setLayout(v_layout)
        # self.helper.setMaximumWidth(200)
        self.layout.set_app_widget(self.helper)

        colors = [Qt.red, Qt.green, Qt.blue, Qt.yellow, Qt.magenta, Qt.cyan, Qt.darkRed, Qt.darkGreen,
                  Qt.darkBlue, Qt.darkYellow, Qt.darkMagenta, Qt.darkCyan, Qt.gray, Qt.darkGray, Qt.lightGray]
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
            data = repl_fontnames(self.renderer.get_filename())
            self.fill_dialog(data)
            self.placeholder.set_progress(self.view.get_page_count())

        self.placeholder.start(process)

    def fill_dialog(self, data):

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
            for font in self.font_manager.filter():
                combobox.addItem(font.full_name)

            item3 = QTreeWidgetItem()
            item.addChild(item3)

            self.treeWidget.invisibleRootItem().addChild(item)
            self.treeWidget.setItemWidget(item3, 0, combobox)
            # self.treeWidget.setMaximumWidth(200)

    def selected(self, text):
        combobox = self.sender()
        item = combobox.item
        item.setForeground(0, Qt.red if text != "Keep" else Qt.black)

    def replace_clicked(self):
        self.placeholder = Progressing(self.view, title="Replacing fonts")

        def process():
            struct = []
            for i in range(self.treeWidget.topLevelItemCount()):
                item = self.treeWidget.topLevelItem(i)
                dic = {"oldfont": [], "newfont": "keep", "info": item.child(0).text(0)}

                old_fonts = item.text(0)
                for elem in old_fonts.split(", "):
                    dic["oldfont"].append(elem)

                combobox = self.treeWidget.itemWidget(item.child(1), 0)
                font_name = combobox.currentText().replace("Keep", "keep")

                if font_name != "keep":
                    font_info = self.font_manager.filter(full_name=font_name)
                    if len(font_info) > 0:
                        dic["newfont"] = font_info[0].path

                struct.append(dic)
                print(dic)

            in_name = self.renderer.get_filename()
            out_name = in_name.replace(".pdf", "_replaced.pdf")

            repl_font(in_name, struct, out_name)
            self.file_generate.emit(out_name, self.view.get_page(), self.view.get_ratio())

        self.placeholder.start(process)

    def finish(self):
        for square in self.squares:
            self.view.scene().removeItem(square)
        self.squares.clear()
        self.layout.remove_app_widget()
        self.helper.deleteLater()
