from PyQt5 import QtGui
from PyQt5.QtCore import QRectF, Qt, pyqtSignal, QItemSelectionModel, QTimer
from PyQt5.QtGui import QPainter, QPixmap, QColor, QFont
from PyQt5.QtWidgets import QPushButton, QColorDialog, QWidget, QSlider, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel, \
    QGroupBox, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QApplication

import utils
from font_manager import FontManager
from progressing import Progressing


class ColorWidget(QPushButton):
    enable = pyqtSignal(bool)

    def __init__(self, color, text=True):
        super().__init__()
        self.color = QColor(color)
        self.has_text = text
        self.opacity = 255
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

    def get_color_with_alpha(self):
        print(self.color.red(), self.color.green(), self.color.blue(), self.opacity)
        return QColor(self.color.red(), self.color.green(), self.color.blue(), self.opacity)

    def set_order(self, order):
        self.order = order

    def choose_color(self):
        color = QColorDialog.getColor(self.color)
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


class Color(QWidget):
    enable = pyqtSignal(bool)

    def __init__(self, color):
        super().__init__()
        r, g, b, a = QColor(color).getRgb()
        print(r, g, b, a, "color")
        self.color_widget = ColorWidget(color)
        self.color_widget.set_order(2)
        self.layout = QFormLayout()
        self.layout.addRow("Color", self.color_widget)
        self.setLayout(self.layout)

    def get_color(self):
        return self.color_widget.get_color()


class ColorAndAlpha(Color):
    def __init__(self, color):
        super().__init__(color)
        r, g, b, a = color.getRgb()
        self.slider = QSlider(Qt.Horizontal)
        self.layout.addRow("Opacity", self.slider)
        self.slider.setRange(0, 255)
        self.slider.valueChanged.connect(self.color_widget.set_opacity)
        self.slider.setValue(a)

    def get_color(self):
        return self.color_widget.get_color_with_alpha()

    def get_opacity(self):
        return self.slider.value() / 100


class ColorAlphaAndWidth(ColorAndAlpha):
    def __init__(self, pen, width=1):
        super().__init__(pen.color())
        self.slider2 = QSlider(Qt.Horizontal)
        self.slider2.setRange(0, 10)
        self.slider2.setValue(pen.width())
        self.layout.addRow("Width", self.slider2)

    def get_width(self):
        return self.slider2.value()


class TextLineEdit(QLineEdit):
    enable = pyqtSignal(bool)

    def __init__(self, text, editable=True):
        super().__init__()
        self.setText(text)
        self.setReadOnly(not editable)

    def set_text(self, text):
        self.setText(text)

    def get_text(self):
        return self.text()


class FontPicker(QWidget):
    enable = pyqtSignal(bool)

    class TreeWidget(QTreeWidget):

        def selectionCommand(self, index, event=None):
            item = self.itemFromIndex(index)
            print("selectionCommand", item, event)
            if item.parent() is None:  # Check if it's a top-level item
                return QItemSelectionModel.NoUpdate
            elif item.path is None:
                return QItemSelectionModel.NoUpdate

            return super().selectionCommand(index, event)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.list_widget = self.TreeWidget()
        self.list_widget.header().hide()
        self.list_widget.setStyleSheet("QListWidget::item { height: 40px; }")
        layout.addWidget(self.list_widget)
        size_layout = QHBoxLayout()
        # pb = QPushButton("Show System Fonts")
        # pb.clicked.connect(self.show_system_fonts)
        # layout.addWidget(pb)
        layout.addLayout(size_layout)
        self.size = QSlider(Qt.Horizontal)
        self.size.setRange(4, 72)
        self.size.valueChanged.connect(self.set_font_size)
        self.size_label = QLabel("")
        self.size_label.setMinimumWidth(30)
        self.size_label.setAlignment(Qt.AlignRight)
        size_layout.addWidget(QLabel("Size"))
        size_layout.addWidget(self.size)
        size_layout.addWidget(self.size_label)
        self.example_label = QLabel()
        self.example_label.setMaximumWidth(300)
        self.example_label.setText("The red fox snuggled up to the lazy dog.")
        gb = QGroupBox("Example")
        gb.setLayout(QVBoxLayout())
        gb.layout().addWidget(self.example_label)
        layout.addWidget(gb)
        self.items = []
        self.list_widget.itemSelectionChanged.connect(self.change_font)
        self.list_widget.setStyleSheet("QTreeView::background-color{background-color:rgb(255,255,255);}")
        QTimer.singleShot(50, self.show_system_fonts)

    def show_system_fonts(self):
        self.pg = Progressing(self, 0, "Loading System Fonts")
        self.pg.start(lambda: self.add_fonts_section("System", FontManager.get_system_fonts()))

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        self.example_label.setMaximumWidth(self.width() - 45)

    def add_fonts_section(self, name, fonts, use_own_font=True):
        # if len(fonts) == 0 and omit_if_empty:
        #    return
        parent = QTreeWidgetItem()
        parent.setText(0, name)
        self.list_widget.addTopLevelItem(parent)

        if len(fonts) == 0:
            item = QTreeWidgetItem()
            item.path = None
            label = QLabel("None")
            label.setEnabled(False)
            parent.addChild(item)
            self.list_widget.setItemWidget(item, 0, label)
            self.items.append(item)
        else:
            for font_info in fonts:
                item = QTreeWidgetItem()
                item.path = font_info['path']
                label = QLabel(font_info['nickname'])
                if use_own_font:
                    font = FontManager.get_qfont_from_ttf(item.path)
                    label.setFont(font)
                parent.addChild(item)
                self.list_widget.setItemWidget(item, 0, label)
                self.items.append(item)

    def set_default(self, ttf_file_name, size):
        self.size.setValue(int(size))
        for item in self.items:
            print("test", item.path, ttf_file_name)
            if item.path == ttf_file_name:
                print("done")
                self.list_widget.setCurrentItem(item)
                item.parent().setExpanded(True)
                break

    def set_default_id(self, section_id, item_id, size):
        self.size.setValue(size)
        if self.list_widget.topLevelItemCount() > section_id:
            top_level = self.list_widget.topLevelItem(section_id)
            if top_level.childCount() > item_id:
                self.list_widget.setCurrentItem(top_level.child(item_id))

    def change_font(self):
        font = FontManager.get_qfont_from_ttf(self.get_font_filename(), self.size.value())
        self.example_label.setFont(font)
        self.example_label.update()
        self.enable.emit(True)

    def set_font_size(self, size):
        self.size_label.setText(str(size))
        font = self.example_label.font()
        font.setPointSize(size)
        self.example_label.setFont(font)

    def get_font_filename(self):
        return self.list_widget.selectedItems()[0].path

    def get_font_size(self):
        return self.size.value()

    def get_font(self):
        return FontManager.get_qfont_from_ttf(self.get_font_filename(), self.size.value())
