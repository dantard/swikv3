import typing
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QGraphicsTextItem, QMenu, QGraphicsRectItem, QGraphicsItem

import utils
from colorwidget import FontPicker, Color
from dialogs import ComposableDialog
from font_manager import FontManager


class SwikText(QGraphicsTextItem):
    def __init__(self, text, parent, font_manager, font, size=11):
        super(SwikText, self).__init__()
        self.font_manager = font_manager
        self.setParentItem(parent)
        self.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        self.ttf_filename = None
        document = self.document()
        document.setDocumentMargin(9)
        self.setDocument(document)
        self.setDefaultTextColor(Qt.red)
        self.document().setPlainText(text)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges, True)
        self.set_ttf_font(font, size)

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        # WARNING: This must be the first line of the method
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # This Line specifies that the event has been already handled
        event.accept()

        menu = QMenu()
        action = menu.addAction("Edit Font")
        res = menu.exec(event.screenPos())
        if res == action:
            font_dialog = ComposableDialog(False)
            fp = font_dialog.add_row("Font", FontPicker())
            # fp.add_fonts_section("Current", [FontManager.get_font_info(self.get_ttf_filename())])
            fp.add_fonts_section("Fully Embedded", self.font_manager.get_fully_embedded_fonts())
            #fp.add_fonts_section("Subset", self.font_manager.get_subset_fonts())
            fp.add_fonts_section("Swik Fonts", self.font_manager.get_swik_fonts())
            fp.add_fonts_section("Base14 Fonts", self.font_manager.get_base14_fonts())
            fp.set_default(self.get_ttf_filename(), self.get_font_size())

            font_dialog.add_row("Text Color", Color(self.defaultTextColor()))
            if font_dialog.exec() == ComposableDialog.Accepted:
                self.set_ttf_font(font_dialog.get("Font").get_font_filename(), font_dialog.get("Font").get_font_size())
                self.setDefaultTextColor(font_dialog.get("Text Color").get_color())

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        self.setTextInteractionFlags(Qt.TextEditable)
        self.setFocus()

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: typing.Any) -> typing.Any:
        if self.parentItem() is not None and change == QGraphicsItem.ItemPositionChange:
            if value.x() < 0:
                value = QPointF(0, value.y())
            elif value.x() + self.boundingRect().width() > self.parentItem().boundingRect().width():
                value = QPointF(self.parentItem().boundingRect().width() - self.boundingRect().width(), value.y())

            if value.y() < 0:
                value = QPointF(value.x(), 0)
            elif value.y() + self.boundingRect().height() > self.parentItem().boundingRect().height():
                value = QPointF(value.x(), self.parentItem().boundingRect().height() - self.boundingRect().height())

        return super().itemChange(change, value)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self.setTextInteractionFlags(Qt.NoTextInteraction)

        self.update()

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)
        print("Focus in")
        self.update()

    def get_rect_on_parent(self):
        return self.parentItem().mapRectFromItem(self, self.boundingRect())

    def get_text(self):
        return self.document().toPlainText()

    def set_text(self, text):
        self.document().setPlainText(text)

    def set_ttf_font(self, filename, size=11):
        document = self.document()
        document.setDocumentMargin(9 / 34 * size)
        self.setDocument(document)

        self.ttf_filename = filename
        font = FontManager.get_qfont_from_ttf(filename, size)
        self.setFont(font)

    def get_ttf_filename(self):
        return self.ttf_filename

    def set_font(self, font, size=None):
        super().setFont(font)
        if size is not None:
            self.set_size(size)
        self.update()

    def set_size(self, size):
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
        self.update()

    def get_font_size(self):
        return self.font().pointSize()
