from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QFormLayout, QComboBox, QVBoxLayout, QLineEdit, QDialog, QDialogButtonBox

import swik.utils as utils
from swik.bunch import NumerateBunch
from swik.dialogs import FontAndColorDialog
from swik.font_manager import Font
from swik.interfaces import Shell
from swik.swik_text import SwikTextNumerate
from swik.tools.tool import BasicTool


class EnumerateDialog(QDialog):

    def __init__(self, view, font_manager):
        super().__init__()
        self.view = view
        self.font_manager = font_manager
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
        self.style_cb.addItems(["Arabic (1, 2, ...)", "Roman (lvxi, ...)", "Roman (LVI, ...)"])

        self.oddeven_db = QComboBox()
        self.oddeven_db.addItems(["Both", "Odd", "Even"])

        f_layout.addRow("Style", self.style_cb)
        f_layout.addRow("From", self.from_cb)
        f_layout.addRow("To", self.to_cb)
        f_layout.addRow("Start with", self.first_page)
        f_layout.addRow("Text", self.text_te)
        f_layout.addRow("Pages", self.oddeven_db)

        font = Font("fonts/Arial.ttf")
        self.font_btn = QPushButton(font.full_name)
        self.font_btn.setFont(font.get_qfont())
        self.font_btn.clicked.connect(self.font_clicked)
        f_layout.addRow("Font", self.font_btn)

        anchor_cb = QComboBox()
        anchor_cb.addItems(["Top Left", "Top Right", "Bottom Left", "Bottom Right"])
        f_layout.addRow("Anchor", anchor_cb)

        # self.layout.addStretch(1)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def font_clicked(self):
        font_dialog = FontAndColorDialog(self.font_manager, Font("fonts/Arial.ttf"), 11, Qt.black)
        if font_dialog.exec() == FontAndColorDialog.Accepted:
            font, color = font_dialog.get("Font"), font_dialog.get("Text Color")
            self.font_btn.setFont(font.get_font().get_qfont())
            self.font_btn.setText(font.get_font().full_name)

    def from_changed(self, index):
        self.to_cb.clear()
        self.to_cb.addItems(str(i) for i in range(index + 1, len(self.view.pages) + 1))
        self.to_cb.setCurrentIndex(self.to_cb.count() - 1)


class ToolNumerate(BasicTool):

    def __init__(self, widget: Shell):
        super(ToolNumerate, self).__init__(widget)
        self.font_manager = widget.get_font_manager()
        self.numbers = []

    def init(self):
        self.view.scene().selectionChanged.connect(self.selection_changed)
        self.layout = QVBoxLayout()
        create_btn = QPushButton("Create")
        remove_btn = QPushButton("Remove All")
        self.layout.addWidget(create_btn)
        self.layout.addWidget(remove_btn)

        create_btn.clicked.connect(self.create)
        self.widget.set_app_widget(self.layout, 125, "Numerate")

    def selection_changed(self):
        print("Selection changed")

    def create(self):
        dialog = EnumerateDialog(self.view, self.font_manager)
        if dialog.exec() == QDialog.Accepted:

            first = int(dialog.from_cb.currentText()) - 1
            last = int(dialog.to_cb.currentText())
            start = int(dialog.first_page.currentText())
            text = dialog.text_te.text()
            style = dialog.style_cb.currentIndex()
            oddeven = dialog.oddeven_db.currentIndex()

            bunch = NumerateBunch(self.view.scene())
            for j, i in enumerate(range(first, last)):
                if oddeven == 0 or (oddeven == 1 and i % 2 == 0) or (oddeven == 2 and i % 2 == 1):

                    if style == 0:
                        num = str(start + j)
                    elif style == 2:
                        num = utils.int_to_roman(start + j)
                    else:
                        num = utils.int_to_roman(start + j).lower()

                    number = SwikTextNumerate(text.replace("$i", num), self.view.pages[i], self.font_manager,
                                              Font("fonts/Arial.ttf"), 12)
                    number.set_box_color(utils.get_color(self.view.scene().get_bunches_count()))
                    bunch.add(number)

    def mouse_pressed(self, event):
        pass

    def mouse_released(self, event):
        pass

    def mouse_moved(self, event):
        pass

    def mouse_double_clicked(self, event):
        pass

    def finish(self):
        #        self.view.scene().selectionChanged.disconnect(self.selection_changed)
        self.widget.remove_app_widget()
