from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QGraphicsProxyWidget, QTextEdit, QLineEdit, QCheckBox, QComboBox, QRadioButton


class PdfWidget(QGraphicsProxyWidget):
    count = 0

    def __init__(self, parent, content, rect, font_size):
        super(QGraphicsProxyWidget, self).__init__(parent)
        self.content = content
        self.widget = self.set_widget(content)
        font = self.widget.font()
        font.setPointSizeF(font_size if font_size else 9)
        self.widget.setFont(font)
        self.widget.setContentsMargins(0, 0, 0, 0)
        self.widget.setFixedSize(int(rect.width()), int(rect.height()))
        self.setWidget(self.widget)
        self.resize(rect.width(), rect.height())
        self.setPos(rect.topLeft())
        self.name = ""
        self.flags = 0
        self.unique_id = PdfWidget.count
        self.user_data = None
        self.xref = -1
        self.on_state = "Yes"
        PdfWidget.count += 1

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

    def clear(self):
        raise NotImplementedError("Subclasses must implement this method")


class PdfTextWidget(PdfWidget):
    def __init__(self, parent, content, rect, font_size):
        super(PdfTextWidget, self).__init__(parent, content.strip(" "), rect, font_size)
        self.widget.setStyleSheet("background-color: lightblue;")

    def set_widget(self, content):
        le = QLineEdit()
        le.setText(content)
        return le

    def get_value(self):
        return self.widget.text() if self.widget.text() != "" else " "

    def clear(self):
        self.widget.setText("")


class MultiLinePdfTextWidget(PdfTextWidget):
    def set_widget(self, content):
        te = QTextEdit()
        te.setText(content)
        return te

    def get_value(self):
        return self.widget.document().toPlainText()

    def clear(self):
        self.widget.document().setPlainText(" ")


class PdfCheckboxWidget(PdfWidget):
    def set_widget(self, content):
        print("Content: ", content)
        cb = QCheckBox()
        cb.setChecked(content == "On" or content == "Yes" or content == "True" or content == "1" or content == True)
        return cb

    def get_value(self):
        # return self.widget.isChecked()
        return self.widget.isChecked()

    def clear(self):
        self.widget.setChecked(False)


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

    def clear(self):
        self.widget.setCurrentIndex(0)


class PdfRadioButtonWidget(PdfWidget):
    def set_widget(self, content):
        print("Content: ", content)
        cb = QRadioButton()
        cb.setChecked(content == "On" or content == "Yes" or content == "True" or content == "1" or content == True)
        cb.setAutoExclusive(False)
        return cb

    def get_value(self):
        return self.widget.isChecked()

    def clear(self):
        self.widget.setChecked(False)
