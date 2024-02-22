from PyQt5 import QtGui
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QPainter, QPixmap, QColor
from PyQt5.QtWidgets import QPushButton, QColorDialog, QWidget, QSlider, QVBoxLayout, QHBoxLayout, QFormLayout


class ColorWidget(QPushButton):
    def __init__(self, color, text=True):
        super().__init__()
        self.color = color
        self.has_text = text
        self.opacity = 1
        self.order = 0
        self.clicked.connect(self.choose_color)

    def set_color(self, color):
        self.color = color
        self.update()

    def set_opacity(self, opacity):
        self.opacity = opacity
        self.update()

    def get_color(self):
        return self.color

    def set_order(self, order):
        self.order = order

    def choose_color(self):
        color = QColorDialog.getColor()
        # color.setAlpha(self.opacity_slider.value())
        if color.isValid():
            self.set_color(color)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        painter = QPainter(self)
        qr = QRectF(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())

        def draw_text():
            if self.has_text:
                painter.drawText(qr, Qt.AlignCenter, "Example Text")

        def draw_color():
            pixmap = QPixmap(self.rect().width(), self.rect().height())
            # print(self.color.red(), self.color.green(), self.color.blue(), int(self.opacity * 255))
            if self.color != Qt.transparent:
                color = QColor(self.color.red(), self.color.green(), self.color.blue(), int(self.opacity))
                pixmap.fill(color)
                painter.drawPixmap(0, 0, pixmap)

        if self.order == 1:
            draw_color()
            draw_text()
        else:
            draw_text()
            draw_color()


class ColorAndAlpha(QWidget):
    def __init__(self, color, opacity=255):
        super().__init__()
        self.color_widget = ColorWidget(color)
        self.color_widget.set_order(2)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 255)
        self.slider.setValue(opacity)
        self.layout = QFormLayout()
        self.layout.addRow("Color", self.color_widget)
        self.layout.addRow("Opacity", self.slider)
        self.slider.valueChanged.connect(self.color_widget.set_opacity)
        self.setLayout(self.layout)

    def get_color(self):
        return self.color_widget.get_color()

    def get_opacity(self):
        return self.slider.value() / 100


class ColorAlphaWidth(ColorAndAlpha):
    def __init__(self, color, opacity=255, width=1):
        super().__init__(color, opacity)
        self.slider2 = QSlider(Qt.Horizontal)
        self.slider2.setRange(0, 10)
        self.slider2.setValue(width)
        self.layout.addRow("Width", self.slider2)

    def get_width(self):
        return self.slider.value() / 100
