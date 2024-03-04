import typing
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QGraphicsTextItem, QMenu


class SwikText(QGraphicsTextItem):
    def __init__(self, text, parent):
        super(SwikText, self).__init__()
        self.setParentItem(parent)
        self.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        self.ttf_filename = None
        document = self.document()
        document.setDocumentMargin(9)
        self.setDocument(document)
        self.setDefaultTextColor(Qt.red)
        self.document().setPlainText(text)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable, True)

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        # WARNING: This must be the first line of the method
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # This Line specifies that the event has been already handled
        event.accept()

        menu = QMenu()
        action = menu.addAction("Edit Fontass")
        menu.exec(event.screenPos())

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        self.setTextInteractionFlags(Qt.TextEditable)
        self.setFocus()

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: typing.Any) -> typing.Any:
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

    def set_ttf_font(self, filename, size=None):
        document = self.document()
        document.setDocumentMargin(9 / 34 * size)
        self.setDocument(document)

        self.ttf_filename = filename
        idx = QFontDatabase.addApplicationFont(filename)
        family = QFontDatabase.applicationFontFamilies(idx)[0]
        self.set_font(QFont(family), size)

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
