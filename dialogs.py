from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFormLayout, QDialogButtonBox, QDialog, QLabel, QVBoxLayout, QGroupBox, QLineEdit, QCheckBox


class ComposableDialog(QDialog):
    def __init__(self, start_enabled=True):
        super().__init__()
        self.rows = {}
        self.initUI()
        if not start_enabled:
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def initUI(self):
        self.setWindowTitle('Simple Dialog')

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
