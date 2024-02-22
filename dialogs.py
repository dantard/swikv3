from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFormLayout, QDialogButtonBox, QDialog, QLabel, QVBoxLayout, QGroupBox

class ComposableDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.rows = {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Simple Dialog')

        layout = QVBoxLayout()

        self.setLayout(layout)

    def exec(self):
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)
        return super().exec()

    def add_row(self, label, widget):
        layout = QVBoxLayout()

        gb = QGroupBox(label)
        gb.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        self.rows[label] = widget
        layout.addWidget(widget)
        self.layout().addWidget(gb)

    def get(self, label):
        return self.rows[label]
