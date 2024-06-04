from PyQt5.QtCore import QMimeData, QUrl, Qt, QPointF
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QFormLayout, QComboBox, QVBoxLayout, QLineEdit

import utils
from bunch import Bunch, AnchoredBunch, NumerateBunch
from dialogs import FontAndColorDialog
from font_manager import Font
from swiktext import SwikTextNumerate
from tools.tool import BasicTool, Tool


class ToolNumerate(BasicTool):
    def __init__(self, name, icon, parent, **kwargs):
        super(ToolNumerate, self).__init__(name, icon, parent)
        self.font_manager = kwargs.get('font_manager')
        self.numbers = []
        self.widget = kwargs.get('widget')

    def init(self):
        self.view.scene().selectionChanged.connect(self.selection_changed)
        self.layout = QVBoxLayout()
        f_layout = QFormLayout()
        self.layout.addLayout(f_layout)
        self.from_cb = QComboBox()
        self.from_cb.addItems(str(i) for i in range(1, len(self.view.pages) + 1))
        self.from_cb.currentIndexChanged.connect(self.from_changed)

        self.to_cb = QComboBox()
        self.from_changed(0)

        self.first_page = QComboBox()
        self.first_page.addItems(str(i) for i in range(1, len(self.view.pages) + 1))

        self.text_te = QLineEdit("$i")
        self.text_te.setAlignment(Qt.AlignCenter)
        self.text_te.setPlaceholderText("Use $i for the number")

        self.style_cb = QComboBox()
        self.style_cb.addItems(["56", "lvi", "LVI"])

        f_layout.addRow("Style", self.style_cb)
        f_layout.addRow("From", self.from_cb)
        f_layout.addRow("To", self.to_cb)
        f_layout.addRow("Start with", self.first_page)
        f_layout.addRow("Text", self.text_te)

        font = Font("fonts/Arial.ttf")
        self.font_btn = QPushButton(font.full_name)
        self.font_btn.setFont(font.get_qfont())
        self.font_btn.clicked.connect(self.font_clicked)
        f_layout.addRow("Font", self.font_btn)

        anchor_cb = QComboBox()
        anchor_cb.addItems(["Top Left", "Top Right", "Bottom Left", "Bottom Right"])
        f_layout.addRow("Anchor", anchor_cb)

        self.layout.addStretch(1)

        remove_btn = QPushButton("Remove All")
        create_btn = QPushButton("Create")
        self.layout.addWidget(remove_btn)
        self.layout.addWidget(create_btn)

        create_btn.clicked.connect(self.create)

        self.widget.set_app_widget(self.layout, 200, "Numerate")

    def selection_changed(self):
        print("Selection changed")

    def font_clicked(self):
        font_dialog = FontAndColorDialog(self.font_manager, Font("fonts/Arial.ttf"), 11, Qt.black)
        if font_dialog.exec() == FontAndColorDialog.Accepted:
            font, color = font_dialog.get("Font"), font_dialog.get("Text Color")
            self.font_btn.setFont(font.get_font().get_qfont())
            self.font_btn.setText(font.get_font().full_name)

    def from_changed(self, index):
        self.to_cb.clear()
        self.to_cb.addItems(str(i) for i in range(index + 1, len(self.view.pages) + 1))

    def create(self):
        first = int(self.from_cb.currentText()) - 1
        last = int(self.to_cb.currentText())
        start = int(self.first_page.currentText())
        text = self.text_te.text()
        style = self.style_cb.currentText()

        bunch = NumerateBunch(self.view.scene())
        for j, i in enumerate(range(first, last)):
            if style == "56":
                num = str(start + j)
            elif style == "LVI":
                num = utils.int_to_roman(start + j)
            else:
                num = utils.int_to_roman(start + j).lower()

            number = SwikTextNumerate(text.replace("$i", num), self.view.pages[i], self.font_manager,
                                      Font("fonts/Arial.ttf"), 12)
            bunch.add(number)

    def mouse_pressed(self, event):
        pass

    def mouse_released(self, event):
        print("clicked")
        pass

    def mouse_moved(self, event):
        pass

    def finish(self):
        self.view.scene().selectionChanged.disconnect(self.selection_changed)
        self.widget.remove_app_widget()
