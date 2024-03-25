from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QProgressDialog, QApplication


class Progressing:
    def __init__(self, parent, max_value=100, title=None):
        self.progress = QProgressDialog(title if title else "Processing", "Cancel", 0, max_value, parent)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setValue(0)
        self.progress.show()
        QApplication.processEvents()
        self.func = None

    def run(self):
        self.update(0)
        self.func()
        self.close()

    def start(self, func):
        self.func = func
        QTimer.singleShot(50, self.run)

    def update(self, value):
        self.progress.setValue(int(value))
        QApplication.processEvents()

    def close(self):
        self.progress.setValue(self.progress.maximum())
        self.progress.close()
