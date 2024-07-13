from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QPushButton


class LongPressButton(QPushButton):
    long_press = pyqtSignal()

    def __init__(self, interval=500, parent=None):
        super().__init__(parent)
        self.setAutoRepeat(True)
        self.setAutoRepeatInterval(interval)
        self.clicked.connect(self.handleClicked)
        self._state = 0

    def handleClicked(self):
        if self.isDown():
            if self._state == 0:
                self._state = 1
            elif self._state == 1:
                self._state = 2
                self.long_press.emit()
            else:
                pass
        else:
            self._state = 0
