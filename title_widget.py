from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QLabel, QSizePolicy, QHBoxLayout, QPushButton, QVBoxLayout, QFrame


class AppBar(QWidget):
    close = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.label = QLabel("Swik")
        font = self.label.font()
        font.setBold(True)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignLeft)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.v_layout = QVBoxLayout()
        self.v_layout.setAlignment(Qt.AlignTop)
        h_layout = QHBoxLayout()
        self.v_layout.addLayout(h_layout)
        h_layout.addWidget(self.label)
        button = QPushButton("✕")
        h_layout.addWidget(button)
        button.setFlat(True)
        button.setFixedSize(20, 20)
        button.clicked.connect(self.close.emit)
        hLine = QFrame()
        hLine.setFrameShape(QFrame.HLine)
        hLine.setFrameShadow(QFrame.Sunken)
        self.v_layout.addWidget(hLine)

        self.setLayout(self.v_layout)
        self.widget = None

    def set_suggested_width(self, width):
        self.setMaximumWidth(width)

    def set_widget(self, widget, title):
        if isinstance(widget, QWidget):
            self.v_layout.addWidget(widget)
        else:
            self.v_layout.addLayout(widget)
        self.set_title(title)

    def remove_widget(self, widget):
        if isinstance(widget, QWidget):
            self.v_layout.removeWidget(widget)
        else:
            self.v_layout.removeItem(widget)
        widget.deleteLater()

    def set_title(self, title):
        self.label.setText(title)
