import typing
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QObject
from PyQt5.QtGui import QFontDatabase, QFont, QColor, QPen
from PyQt5.QtWidgets import QGraphicsTextItem, QMenu, QGraphicsRectItem, QGraphicsItem

import utils
from action import Action
from colorwidget import FontPicker, Color
from dialogs import ComposableDialog, FontAndColorDialog
from font_manager import FontManager
from interfaces import Undoable


class SwikText(QGraphicsTextItem, Undoable):
    class Signals(QObject):
        moved = pyqtSignal(object, QPointF)
        font_changed = pyqtSignal(object, QFont)
        action = pyqtSignal(object, str)
        move_started = pyqtSignal(object)
        move_finished = pyqtSignal(object)

    def __init__(self, text, parent, font_manager, font_info, size=11):
        super(SwikText, self).__init__()
        self.signals = self.Signals()

        # Necessary because of ReplaceSwikText
        self.check_parent_limits = True
        self.font_manager = font_manager
        self.setParentItem(parent)
        self.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        self.font_info = font_info
        self.bg_color = Qt.transparent
        self.setDefaultTextColor(Qt.black)
        self.document().setPlainText(text)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsTextItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges, True)
        self.apply_font(size)
        self.notify_creation(self)
        self.current_pose = None
        self.current_state = None

    def get_font_info(self):
        return self.font_info

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
        print("swiktexct")
        if event.key() == Qt.Key_Plus:
            font = self.font()
            font.setPointSizeF(font.pointSizeF() + 0.1)
            self.setFont(font)
        elif event.key() == Qt.Key_Minus:
            font = self.font()
            font.setPointSizeF(font.pointSizeF() - 0.1)
            self.setFont(font)
        super(SwikText, self).keyPressEvent(event)

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        if not self.isSelected():
            self.setSelected(True)
        # WARNING: This must be the first line of the method
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # This Line specifies that the event has been already handled
        event.accept()
        self.popup_context_menu(QMenu(), event)

    def popup_context_menu(self, menu, event):
        action = menu.addAction("Edit Font")
        res = menu.exec(event.screenPos())
        self.current_state = self.get_full_state()
        if res == action:
            font_dialog = FontAndColorDialog(self.font_manager, self.get_font_info().nickname, self.get_font_size(), self.defaultTextColor())
            if font_dialog.exec() == ComposableDialog.Accepted:
                font, color = font_dialog.get("Font"), font_dialog.get("Text Color")
                self.set_font_info(font.get_font(), font.get_font_size())
                self.setDefaultTextColor(color.get_color())

                self.signals.font_changed.emit(self, self.font())

                if self.current_state != self.get_full_state():
                    self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())

        return res

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseDoubleClickEvent(event)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus()

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mousePressEvent(event)
        self.current_pose = self.pos()

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)
        if self.current_pose != self.pos():
            self.notify_position_change(self.current_pose, self.pos())

    def undo(self, kind, info):
        self.set_full_state(info)

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
        if self.current_state != self.get_full_state():
            self.notify_change(Action.FULL_STATE, self.current_state, self.get_full_state())
        self.update()

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)
        self.current_state = self.get_full_state()
        self.update()

    def get_rect_on_parent(self):
        return self.parentItem().mapRectFromItem(self, self.boundingRect())

    def get_text(self):
        return self.document().toPlainText()

    def set_text(self, text):
        self.document().setPlainText(text)

    def apply_font(self, size):
        document = self.document()
        # TODO: This is a magic number, it should be calculated based on the font size
        document.setDocumentMargin(9 / 34 * size)
        self.setDocument(document)
        qfont = self.font_info.get_qfont(size)
        # qfont.setStretch(98)
        self.setFont(qfont)

    def set_font_info(self, font_info, size=11):
        self.font_info = font_info
        self.apply_font(size)

    def set_font(self, font, size=None):
        super().setFont(font)
        if size is not None:
            self.set_size(size)
        self.update()

    def set_size(self, size):
        font = self.font()
        font.setPointSizeF(size)
        self.setFont(font)
        self.update()

    def get_font_size(self):
        return self.font().pointSizeF()

    # State management
    def get_full_state(self):
        return {"text": self.toPlainText(), "font": self.font_info, "font_size": self.get_font_size(),
                "text_color": self.defaultTextColor()}

    def set_full_state(self, state):
        self.set_common_state(state)
        self.document().setPlainText(state["text"] if "state" in state else self.document().toPlainText())

    def set_common_state(self, state):
        if "font" in state:
            self.set_font_info(state["font"], state["font_size"] if "font_size" in state else None)
        self.setDefaultTextColor(state["text_color"] if "text_color" in state else self.defaultTextColor())

    def get_common_state(self):
        return {"font_ttf_filename": self.ttf_filename, "font_size": self.get_font_size(), "text_color": self.defaultTextColor()}


class SwikTextReplace(SwikText):
    def __init__(self, word, font_manager, font, size, color=Qt.black):
        super(SwikTextReplace, self).__init__(word.get_text(), word.parentItem(), font_manager, font, size)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setZValue(1)
        self.setPos(word.pos() - QPointF(size / 3.5, size / 3.4))
        self.bg = QGraphicsRectItem(self)
        self.bg.setFlag(QGraphicsItem.ItemNegativeZStacksBehindParent)
        self.bg.setPen(QPen(Qt.red))
        self.bg.setBrush(QColor(Qt.white))
        self.bg.setZValue(-1)
        self.bg.setRect(word.rect())
        self.bg.setPos(QPointF(size / 3.5, size / 3.5))
        self.setDefaultTextColor(QColor(color))

    def get_patch_on_page(self):
        pos_on_page = self.parentItem().mapFromScene(self.bg.scenePos())
        return QRectF(pos_on_page, self.bg.rect().size())

    def get_patch_color(self):
        return self.bg.brush().color()


class SwikTextNumerate(SwikText):
    ANCHOR_TOP_LEFT = 0
    ANCHOR_TOP_RIGHT = 1
    ANCHOR_BOTTOM_LEFT = 2
    ANCHOR_BOTTOM_RIGHT = 3
    ANCHOR_TOP_CENTER = 4
    ANCHOR_BOTTOM_CENTER = 5

    def __init__(self, text, parent, font_manager, path, size):
        super(SwikTextNumerate, self).__init__(text, parent, font_manager, path, size)
        self.emit_block = False
        self.anchor = SwikTextNumerate.ANCHOR_TOP_LEFT

    def block_emit(self, value):
        self.emit_block = value

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: typing.Any) -> typing.Any:
        res = super().itemChange(change, value)
        if change == QGraphicsItem.ItemPositionChange:
            if not self.emit_block:
                self.signals.moved.emit(self, self.pos())
        return res

    def popup_context_menu(self, menu, event):
        start_here = menu.addAction("Start Here")
        remove = menu.addAction("Remove")
        remove_all = menu.addAction("Remove all")
        center = menu.addAction("Center")
        menu_anchor = menu.addMenu("Anchor")
        top_left = menu_anchor.addAction("Top Left")
        top_right = menu_anchor.addAction("Top Right")
        bottom_left = menu_anchor.addAction("Bottom Left")
        bottom_right = menu_anchor.addAction("Bottom Right")
        top_center = menu_anchor.addAction("Top Center")
        bottom_center = menu_anchor.addAction("Bottom Center")

        anchor = [top_left, top_right, bottom_left, bottom_right, top_center, bottom_center]
        for a in anchor:
            a.setCheckable(True)
            if anchor.index(a) == self.anchor:
                a.setChecked(True)

        menu.addSeparator()
        before = (self.font(), self.defaultTextColor())

        res = super().popup_context_menu(menu, event)

        if res == start_here:
            self.signals.action.emit(self, "start_here")
        elif res == remove_all:
            self.signals.action.emit(self, 'remove_all')
        elif res == remove:
            self.signals.action.emit(self, 'remove')
        elif res in anchor:
            self.anchor = anchor.index(res)
            self.signals.action.emit(self, 'anchor_changed')
        elif res == center:
            self.signals.action.emit(self, 'center')

        if before != (self.font(), self.defaultTextColor()):
            self.signals.font_changed.emit(self, self.font())
