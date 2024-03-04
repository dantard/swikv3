from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QTextOption, QTextDocument
from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsRectItem, QApplication, QGraphicsProxyWidget, QTextEdit, QLineEdit, QCheckBox, QComboBox


class PdfWidget(QGraphicsProxyWidget):
    def __init__(self, parent, content, rect, font_size):
        super(QGraphicsProxyWidget, self).__init__(parent)
        self.content = content
        self.widget = self.set_widget(content)
        font = self.widget.font()
        font.setPointSizeF(font_size if font_size else 9)
        self.widget.setFont(font)
        self.widget.setContentsMargins(0, 0, 0, 0)
        self.widget.setStyleSheet("background-color: lightblue;")
        self.widget.setFixedSize(int(rect.width()), int(rect.height()))
        self.setWidget(self.widget)
        self.resize(rect.width(), rect.height())
        self.setPos(rect.topLeft())
        self.name = ""
        self.flags = 0

    def set_info(self, name, flags):
        self.name = name
        self.flags = flags

    def get_info(self):
        return self.name, self.flags

    def get_content(self):
        return self.content

    def get_rect(self):
        return QRectF(self.pos(), self.size())

    def set_content(self, content):
        self.content = content

    def set_widget(self, content):
        raise NotImplementedError("Subclasses must implement this method")

    def get_value(self):
        raise NotImplementedError("Subclasses must implement this method")


class PdfTextWidget(PdfWidget):
    def set_widget(self, content):
        le = QLineEdit()
        le.setText(content)
        return le

    def get_value(self):
        return self.widget.text()


class MultiLinePdfTextWidget(PdfTextWidget):
    def set_widget(self, content):
        te = QTextEdit()
        te.setText(content)
        return te

    def get_value(self):
        return self.widget.document().toPlainText()


class PdfCheckboxWidget(PdfTextWidget):
    def set_widget(self, content):
        print("Content: ", content)
        cb = QCheckBox()
        cb.setChecked(content == "On" or content == "Yes" or content == "True" or content == "1")
        return cb

    def get_value(self):
        return "Yes" if self.widget.isChecked() else "Off"


class PdfComboboxWidget(PdfTextWidget):

    def __init__(self, parent, content, rect, font_size, items):
        super().__init__(parent, content, rect, font_size)
        self.add_items(items)
        self.setZValue(1)

    def set_widget(self, content):
        cb = QComboBox()
        cb.setCurrentText(content)
        return cb

    def add_items(self, items):
        self.widget.addItems(items)

    def get_items(self):
        return [self.widget.itemText(i) for i in range(self.widget.count())]

    def get_value(self):
        return self.widget.currentText()


