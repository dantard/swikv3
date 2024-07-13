from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, \
    QPushButton, QWidget

from swik import utils
from swik.font_manager import FontManager, Arial

from swik.dialogs import FontAndColorDialog, ComposableDialog
from swik.interfaces import Shell
from swik.page import Page
from swik.progressing import Progressing
from swik.swik_text import SwikText, SwikTextReplace, SwikTextMimic
from swik.tools.tool import Tool


class ToolMimicPDF(Tool):
    file_generate = pyqtSignal(str, int, float)

    def __init__(self, widget: Shell):
        super(ToolMimicPDF, self).__init__(widget)
        self.placeholder = None
        self.font_manager = widget.get_font_manager()
        self.squares = []
        self.app = None
        self.texts = []
        self.helper = None
        self.tree = None

    def init(self):
        self.texts.clear()
        self.squares.clear()
        self.v_layout = QVBoxLayout()
        self.helper = QWidget()
        self.helper.setContentsMargins(0, 0, 0, 0)
        self.helper.setLayout(self.v_layout)
        self.helper.layout().setAlignment(Qt.AlignTop)
        self.helper.layout().setContentsMargins(0, 0, 0, 0)
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self.generate)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply)
        self.apply_btn.setEnabled(False)

        self.colorize_btn = QPushButton("Colorize")
        self.colorize_btn.setCheckable(True)
        self.colorize_btn.clicked.connect(self.colorize_btn_clicked)

        self.clear_btn = QPushButton("×")
        self.clear_btn.clicked.connect(self.clear)
        self.clear_btn.setFixedSize(25, 25)
        self.clear_btn.setEnabled(False)

        self.transparent_btn = QPushButton("•")
        self.transparent_btn.clicked.connect(self.transparent_btn_clicked)
        self.transparent_btn.setFixedSize(25, 25)
        self.transparent_btn.setCheckable(True)
        self.transparent_btn.setEnabled(False)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Font", "Replace"])
        self.v_layout.addWidget(self.tree)
        self.v_layout.addWidget(self.colorize_btn)

        self.v_layout.addLayout(utils.row(self.generate_btn, self.transparent_btn, False))
        self.v_layout.addLayout(utils.row(self.apply_btn, self.clear_btn, False))

        self.widget.set_app_widget(self.helper, 300, title="Mimic PDF")
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

    def transparent_btn_clicked(self):
        for page in self.view.pages.values():
            items = page.items(SwikTextMimic)
            for item in items:
                if self.transparent_btn.isChecked():
                    item.set_bg_color(QColor(0, 0, 0, 0))
                else:
                    item.set_bg_color(QColor(255, 255, 255, 255))

    def clear(self):
        for page in self.view.pages.values():
            for item in page.items(SwikTextMimic):
                self.view.scene().removeItem(item)

        self.clear_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.widget.set_protected_interaction(True)
        self.generate_btn.setEnabled(True)
        self.transparent_btn.setEnabled(False)
        self.colorize_btn.setEnabled(True)

    def apply(self):
        self.placeholder = Progressing(self.view, 0, "Applying changes", cancel=True)

        def apply():
            self.renderer.sync_requested.emit()
            self.view.pages[0].invalidate()
            filename = self.renderer.get_filename().replace(".pdf", "-mimic.pdf")
            self.renderer.save_elsewhere(filename)
            self.widget.open_requested.emit(filename, self.view.page, self.view.get_ratio())
            self.placeholder.close()

        self.placeholder.start(apply)

    def colorize_btn_clicked(self):
        self.colorize(self.sender().isChecked())
        self.generate_btn.setEnabled(not self.sender().isChecked())

    def colorize(self, checked: bool):
        colors = [Qt.red, Qt.green, Qt.blue, Qt.yellow, Qt.magenta, Qt.cyan, Qt.darkRed, Qt.darkGreen,
                  Qt.darkBlue, Qt.darkYellow, Qt.darkMagenta, Qt.darkCyan, Qt.gray, Qt.darkGray, Qt.lightGray]

        if checked:

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

        for i in self.texts:
            self.view.scene().removeItem(i)
        self.texts.clear()

        self.progressing = Progressing(self.view, self.view.get_page_count(), "Generating PDF", cancel=True)

        def process():
            for i in range(0, self.view.get_page_count()):
                if not self.progressing.set_progress(i):
                    break
                page: Page = self.view.pages[i]

                items = page.items(SwikTextReplace)
                for item in items:
                    self.view.scene().removeItem(item)

                page.gather_words()

                for word in page.get_words():
                    font_name, size, color = self.renderer.get_word_font_info(word)
                    new_font_name = translate.get(font_name)
                    font = self.font_manager.filter(nickname=new_font_name, pos=0)
                    if font:
                        border = Qt.blue
                    else:
                        font = Arial()
                        border = Qt.red
                    mimic = SwikTextMimic(word, self.font_manager, font, size / (96.0 / 72.0), QColor(color))
                    mimic.set_border_color(border)

                    if self.transparent_btn.isChecked():
                        mimic.set_bg_color(QColor(0, 0, 0, 0))
                    else:
                        mimic.set_bg_color(QColor(255, 255, 255, 255))

            self.progressing.setValue(self.view.get_page_count())

            self.clear_btn.setEnabled(True)
            self.widget.set_protected_interaction(False)
            self.apply_btn.setEnabled(True)
            self.generate_btn.setEnabled(False)
            self.transparent_btn.setEnabled(True)
            self.colorize_btn.setEnabled(False)

        self.progressing.start(process)

    def finish(self):
        self.clear()
        self.colorize(False)
        self.widget.remove_app_widget()
