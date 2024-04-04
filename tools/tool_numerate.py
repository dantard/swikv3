from PyQt5.QtCore import QMimeData, QUrl, Qt, QPointF
from PyQt5.QtGui import QDrag

from swiktext import SwikTextNumerate
from tools.tool import BasicTool, Tool


class ToolNumerate(Tool):
    def __init__(self, name, icon, parent, **kwargs):
        super(ToolNumerate, self).__init__(name, icon, parent)
        self.font_manager = kwargs.get('font_manager')
        self.numbers = []

    def init(self):
        for i in range(0, self.view.get_page_count()):
            number = SwikTextNumerate(str(i + 1), self.view.pages[i], self.font_manager, '@base14/helv', 12)
            number.signals.moved.connect(self.moved)
            number.signals.font_changed.connect(self.font_changed)
            number.signals.action.connect(self.action)
            self.numbers.append(number)

    def moved(self, obj, pos):
        print('update')
        for number in self.numbers:
            if number != obj:
                number.block_emit(True)
                if number.anchor == SwikTextNumerate.ANCHOR_TOP_LEFT:
                    number.setPos(pos)
                elif number.anchor == SwikTextNumerate.ANCHOR_TOP_RIGHT:
                    obj_x_pos = obj.parentItem().boundingRect().width() - obj.pos().x()
                    number.setPos(number.parentItem().boundingRect().width() - obj_x_pos, obj.pos().y())
                elif number.anchor == SwikTextNumerate.ANCHOR_BOTTOM_LEFT:
                    obj_y_pos = obj.parentItem().boundingRect().height() - obj.pos().y()
                    number.setPos(obj.pos().x(), number.parentItem().boundingRect().height() - obj_y_pos)
                elif number.anchor == SwikTextNumerate.ANCHOR_BOTTOM_RIGHT:
                    obj_x_pos = obj.parentItem().boundingRect().width() - obj.pos().x()
                    obj_y_pos = obj.parentItem().boundingRect().height() - obj.pos().y()
                    number.setPos(number.parentItem().boundingRect().width() - obj_x_pos, number.parentItem().boundingRect().height() - obj_y_pos)
                elif number.anchor == SwikTextNumerate.ANCHOR_TOP_CENTER:
                    delta_x = obj.pos().x() - obj.parentItem().boundingRect().width() / 2
                    number.setPos(number.parentItem().boundingRect().width() / 2 + delta_x, obj.pos().y())
                elif number.anchor == SwikTextNumerate.ANCHOR_BOTTOM_CENTER:
                    obj_y_pos = obj.parentItem().boundingRect().height() - obj.pos().y()
                    number.setPos(obj.parentItem().boundingRect().width() / 2, number.parentItem().boundingRect().height() - obj_y_pos)
                number.block_emit(False)

    def font_changed(self, obj, font):
        for number in self.numbers:
            if number != obj:
                number.set_font(font)

    def action(self, obj, action):
        if action == 'remove':
            self.view.scene().removeItem(obj)
            self.numbers.remove(obj)
        elif action == 'start_here':
            index = self.numbers.index(obj)
            for number in self.numbers[:index]:
                self.view.scene().removeItem(number)
            self.numbers = self.numbers[index:]
            for i, number in enumerate(self.numbers):
                number.set_text(str(i + 1))
        elif action == 'remove_all':
            for number in self.numbers:
                self.view.scene().removeItem(number)
            self.numbers.clear()
        elif action == 'anchor_changed':
            print("anchor changed")
            anchor = obj.anchor
            for number in self.numbers:
                if number != obj:
                    number.anchor = anchor
                    self.moved(obj, obj.pos())
        elif action == 'center':
            # obj.setPos(QPointF(obj.parentItem().boundingRect().width() / 2 - obj.boundingRect().width() / 2, obj.pos().y()))

            for number in self.numbers:
                number.block_emit(True)
                number.setPos(number.parentItem().boundingRect().width() / 2 - number.boundingRect().width() / 2, number.pos().y())
                number.block_emit(False)

                # number.update()
