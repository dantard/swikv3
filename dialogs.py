from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFormLayout, QDialogButtonBox, QDialog, QLabel, QVBoxLayout, QGroupBox, QLineEdit, QCheckBox

from colorwidget import FontPicker, Color
from dict_editor import DictTreeWidget


class ComposableDialog(QDialog):
    def __init__(self, start_enabled=True, title="Edit"):
        super().__init__()
        self.rows = {}
        self.initUI(title)
        if not start_enabled:
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def set_ok_enabled(self, enabled):
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(enabled)

    def initUI(self, title):
        self.setWindowTitle(title)

        layout = QVBoxLayout()

        self.setLayout(layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

    def exec(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout().addWidget(self.button_box)
        return super().exec()

    def add_row(self, label, widget):
        layout = QVBoxLayout()
        widget.enable.connect(lambda x: self.button_box.button(QDialogButtonBox.Ok).setEnabled(x))

        gb = QGroupBox(label)
        gb.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        self.rows[label] = widget
        layout.addWidget(widget)
        self.layout().addWidget(gb)
        return widget

    def get(self, label):
        return self.rows[label]


class PasswordDialog(QDialog):
    def __init__(self, checkbox=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password")
        layout = QVBoxLayout(self)
        self.lb = QLabel("Password")
        self.le = QLineEdit()
        self.le.setEchoMode(QLineEdit.Password)
        self.cb = QCheckBox("Save Password")
        layout.addWidget(self.lb)
        layout.addWidget(self.le)
        if checkbox:
            layout.addWidget(self.cb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(bb)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)

    def getText(self):
        return self.le.text()

    def getCheckBox(self):
        return self.cb.isChecked()

    def closeEvent(self, a0):
        pass


class FontAndColorDialog(ComposableDialog):
    def __init__(self, font_manager, default, font_size, text_color):
        super().__init__()
        self.font_manager = font_manager
        fp = self.add_row("Font", FontPicker())
        # fp.add_fonts_section("Current", [FontManager.get_font_info(self.get_ttf_filename())])
        fp.add_fonts_section("Fully Embedded", self.font_manager.get_fully_embedded_fonts())
        fp.add_fonts_section("Subset", self.font_manager.get_subset_fonts(), False)
        fp.add_fonts_section("Swik Fonts", self.font_manager.get_swik_fonts())
        fp.add_fonts_section("Base14 Fonts", self.font_manager.get_base14_fonts())
        fp.set_default(default, font_size)
        self.add_row("Text Color", Color(text_color))
        self.set_ok_enabled(default is not None)

    def get_font_filename(self):
        return self.get('Font').get_font_filename()

    def get_font_size(self):
        return self.get('Font').get_font_size()

    def get_text_color(self):
        return self.get('Text Color').get_color()


def FontTextAndColor(FontAndColorDialog):
    pass


class ReplaceFontsDialog(QDialog):
    def __init__(self, data):
        super().__init__()

        # Initialize the dialog window
        self.setWindowTitle("My Dialog")

        # Create a QTreeWidget
        self.treeWidget = DictTreeWidget()
        self.treeWidget.setHeaderLabels(["Items"])
        self.treeWidget.set_data(data)

        # Create standard OK and Cancel buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.treeWidget)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

    def get_data(self):
        return  self.treeWidget.traverse_tree(self.treeWidget.invisibleRootItem().child(0))
