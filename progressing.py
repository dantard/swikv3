import time

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtWidgets import QProgressDialog, QApplication, QWidget, QProgressBar, QVBoxLayout, QPushButton, QMainWindow, QDialog, QLabel


class Progressing(QDialog):
    done = pyqtSignal(object)

    def __init__(self, parent, max_value=0, title=None, cancel=False):
        super().__init__(parent)
        self.widget_layout = QVBoxLayout()
        self.setLayout(self.widget_layout)
        self.bar = QProgressBar()
        self.been_canceled = False
        self.callback = None
        self.func = None
        self.args = None
        self.ret_value = None

        if max_value > 0:
            self.bar.setRange(0, max_value)
        else:
            self.bar.setRange(0, 100)
            self.bar.setValue(100)

        self.bar.setTextVisible(False)
        self.setWindowTitle("Processing")
        if title:
            self.layout().addWidget(QLabel(title))

        self.widget_layout.addWidget(self.bar)

        if cancel:
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.clicked.connect(self.cancel_clicked)
            self.widget_layout.addWidget(self.cancel_button)
        self.show()
    def set_progress(self, value):
        if self.been_canceled:
            return False
        self.bar.setValue(value)
        #QApplication.processEvents()
        if self.bar.value() == self.bar.maximum():
            self.hide()
            self.done.emit(None)
            if self.callback:
                self.callback(None)
        return True

    def run(self):
        self.ret_value = self.func(*self.args)
        self.hide()
        self.done.emit(self.ret_value)
        if self.callback:
            self.callback(self.ret_value)

    def get_return_value(self):
        return self.ret_value

    def start(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.callback = kwargs.get('callback', None)
        QTimer.singleShot(150, self.run)

    def cancel_clicked(self):
        self.been_canceled = True

    def canceled(self):
        return self.been_canceled
