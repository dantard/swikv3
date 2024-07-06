from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QFormLayout, QComboBox, QVBoxLayout, QLineEdit, QDialog, QDialogButtonBox

import swik.utils as utils
from swik.bunch import NumerateBunch
from swik.dialogs import FontAndColorDialog, EnumerateDialog
from swik.font_manager import Font, Arial
from swik.interfaces import Shell
from swik.swik_text import SwikTextNumerate
from swik.tools.tool import BasicTool


class ToolNumerate(BasicTool):

    def __init__(self, widget: Shell):
        super(ToolNumerate, self).__init__(widget)
        self.font_manager = widget.get_font_manager()

    def init(self):
        self.layout = QVBoxLayout()
        create_btn = QPushButton("Create")
        remove_btn = QPushButton("Remove All")
        self.layout.addWidget(create_btn)
        self.layout.addWidget(remove_btn)
        remove_btn.clicked.connect(self.remove_all)
        create_btn.clicked.connect(self.create)
        self.widget.set_app_widget(self.layout, 125, "Numerate")

    def remove_all(self):
        for bunch in self.view.scene().get_bunches(NumerateBunch):
            bunch.clear()

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

                    number = SwikTextNumerate(text.replace("$i", num), self.view.pages[i], self.font_manager, Arial(), 12)

                    number.set_bg_color(utils.get_color(self.view.scene().get_bunches_count(), 0.3))
                    bunch.add(number)

            bunch.notify_creation()

    def mouse_pressed(self, event):
        pass

    def mouse_released(self, event):
        pass

    def mouse_moved(self, event):
        pass

    def mouse_double_clicked(self, event):
        pass

    def finish(self):
        self.widget.remove_app_widget()
