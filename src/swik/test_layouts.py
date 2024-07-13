import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QSplitter, QHBoxLayout, QPushButton


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        helper = QWidget()
        pb = QPushButton("Hello")
        self.vlayout = QVBoxLayout()
        self.hlayout = QHBoxLayout()
        self.vlayout.addLayout(self.hlayout)
        self.ilayout = QHBoxLayout()
        sp = QSplitter()
        sp.addWidget(pb)
        sp.setOrientation(Qt.Horizontal)
        sp.addWidget(QPushButton("Hello"))
        self.ilayout.addWidget(sp)
        self.hlayout.addLayout(self.ilayout)

        helper.setLayout(self.vlayout)

        pb.setMinimumHeight(200)
        pb.setMinimumWidth(200)

        self.setCentralWidget(helper)

        self.pb2 = QPushButton("Hello2")

        pb.clicked.connect(self.clicked)

    count = 0

    def clicked(self):
        if self.count == 0:
            # self.vlayout.removeWidget(self.pb2)
            self.vlayout.insertWidget(0, self.pb2)
        elif self.count == 1:
            # self.vlayout.removeWidget(self.pb2)
            self.vlayout.insertWidget(self.vlayout.count(), self.pb2)
        elif self.count == 2:
            self.hlayout.insertWidget(0, self.pb2)
        elif self.count == 3:
            self.hlayout.insertWidget(self.hlayout.count(), self.pb2)
        self.count = (self.count + 1) % 4


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
