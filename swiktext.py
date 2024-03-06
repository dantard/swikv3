import typing
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QFontDatabase, QFont, QColor, QPen
from PyQt5.QtWidgets import QGraphicsTextItem, QMenu, QGraphicsRectItem, QGraphicsItem

import utils
from action import Action
from colorwidget import FontPicker, Color
from dialogs import ComposableDialog
from font_manager import FontManager
from interfaces import Undoable


class SwikText(QGraphicsTextItem, Undoable):
    def __init__(self, text, parent, font_manager, font, size=11):
        super(SwikText, self).__init__()
        # Necessary because of ReplaceSwikText
        self.check_parent_limits = True
        self.font_manager = font_manager
        self.setParentItem(parent)
        self.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        self.ttf_filename = None
        self.bg_color = Qt.transparent
        document = self.document()
        document.setDocumentMargin(9)
        self.setDocument(document)
        self.setDefaultTextColor(Qt.red)
        self.document().setPlainText(text)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsTextItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges, True)
        self.set_ttf_font(font, size)
        self.before = None

    def set_background_color(self, color: Color):
        self.bg_color = QColor(color)

    def get_background_color(self):
        return self.bg_color

    def paint(self, painter, o, w):
        painter.setBrush(self.bg_color)
        painter.setPen(Qt.transparent)
        rect = self.boundingRect()
        rect.setWidth(rect.width() - 2)
        painter.drawRect(rect)
        super().paint(painter, o, w)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key_Plus:
            font = self.font()
            font.setPointSizeF(font.pointSizeF() + 1)
            self.setFont(font)
        elif event.key() == Qt.Key_Minus:
            font = self.font()
            font.setPointSizeF(font.pointSizeF() - 1)
            self.setFont(font)
        super(SwikText, self).keyPressEvent(event)

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
            fp.add_fonts_section("Subset", self.font_manager.get_subset_fonts(), False)
            fp.add_fonts_section("Swik Fonts", self.font_manager.get_swik_fonts())
            fp.add_fonts_section("Base14 Fonts", self.font_manager.get_base14_fonts())
            fp.set_default(self.get_ttf_filename(), self.get_font_size())

            font_dialog.add_row("Text Color", Color(self.defaultTextColor()))
            if font_dialog.exec() == ComposableDialog.Accepted:
                self.set_ttf_font(font_dialog.get("Font").get_font_filename(), font_dialog.get("Font").get_font_size())
                self.setDefaultTextColor(font_dialog.get("Text Color").get_color())

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus()

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mousePressEvent(event)
        self.before = self.pos()

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)
        if self.before is not None and self.before != self.pos():
            self.notify_change(Action.POSE_CHANGED, self.before, self.pos())

    def undo(self, kind, info):
        if kind == Action.POSE_CHANGED:
            self.setPos(info)
        elif kind == Action.TEXT_CHANGED:
            self.document().setPlainText(info)

    def redo(self, kind, info):
        self.undo(kind, info)

    def set_check_parent_limits(self, check):
        self.check_parent_limits = check

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: typing.Any) -> typing.Any:
        if self.parentItem() is not None and self.check_parent_limits and change == QGraphicsItem.ItemPositionChange:
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
        if self.text_before != self.toPlainText():
            self.notify_change(Action.TEXT_CHANGED, self.text_before, self.toPlainText())
        self.update()

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)
        print("Focus in")
        self.text_before = self.toPlainText()
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


class SwikTextReplace(SwikText):
    def __init__(self, word, font_manager, path, size):
        super(SwikTextReplace, self).__init__(word.get_text(), word.parentItem(), font_manager, path, size)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setZValue(1)
        self.setPos(word.pos() - QPointF(size / 3.5, size / 3.5))
        self.bg = QGraphicsRectItem(self)
        self.bg.setFlag(QGraphicsItem.ItemNegativeZStacksBehindParent)
        self.bg.setPen(QPen(Qt.red))
        self.bg.setBrush(QColor(Qt.white))
        self.bg.setZValue(-1)
        self.bg.setRect(word.rect())
        self.bg.setPos(QPointF(size / 3.5, size / 3.5))

    def get_patch_on_page(self):
        pos_on_page = self.parentItem().mapFromScene(self.bg.scenePos())
        return QRectF(pos_on_page, self.bg.rect().size())

    def get_patch_color(self):
        return self.bg.brush().color()
