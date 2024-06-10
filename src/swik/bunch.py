from PyQt5.QtCore import QObject

from swik.swiktext import SwikTextNumerate


class Bunch(QObject):

    def __init__(self):
        super(Bunch, self).__init__()
        self.numbers = []

    def add(self, element):
        self.numbers.append(element)


class AnchoredBunch(Bunch):

    def __init__(self, scene):
        super(AnchoredBunch, self).__init__()
        self.scene = scene
        self.scene.bunches.append(self)

    def add(self, element):
        super(AnchoredBunch, self).add(element)
        element.signals.moved.connect(self.moved)

    def moved(self, obj, pos):
        for number in self.numbers:
            if number == obj:
                continue

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


class NumerateBunch(AnchoredBunch):

    def add(self, element):
        super(NumerateBunch, self).add(element)
        element.signals.font_changed.connect(self.font_changed)
        element.signals.action.connect(self.action)

    def font_changed(self, obj, font):
        for number in self.numbers:
            if number != obj:
                number.set_font(font)

    def action(self, obj, action):
        if action == 'remove':
            self.scene.removeItem(obj)
            self.numbers.remove(obj)
        elif action == 'start_here':
            index = self.numbers.index(obj)
            for number in self.numbers[:index]:
                self.scene.removeItem(number)
            self.numbers = self.numbers[index:]
            for i, number in enumerate(self.numbers):
                number.set_text(str(i + 1))
        elif action == 'remove_all':
            for number in self.numbers:
                self.scene.removeItem(number)
            self.numbers.clear()
            self.scene.bunches.remove(self)
        elif action == 'anchor_changed':
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
