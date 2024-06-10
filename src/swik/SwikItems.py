from PyQt5 import QtCore
from PyQt5.QtGui import QBrush, QPen
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem


class SwikSignals(QtCore.QObject):
    POSE = 0
    LOOK = 1
    SHAPE = 2
    changed = QtCore.pyqtSignal(QGraphicsItem, int, dict)


class SwikRectItem(QGraphicsRectItem):
    def __init__(self, parent=None, interactable=True):
        super().__init__(parent)
        self.current_pos = None
        self.current_rect = None
        self.current_look = None
        self.swik_signals = SwikSignals()
        self.content = str()

        if interactable:
            self.add_interaction_frame()
        else:
            self.interaction_frame = None

    def look_edit(self):
        self.current_look = self.get_look()

    def look_done(self):
        if self.current_look != self.get_look():
            self.swik_signals.changed.emit(self, ChangesTracker.LOOK_CHANGED, {'look0': self.current_look, 'look1': self.get_look()})

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        super().hoverEnterEvent(event)
        if self.interaction_frame is not None:
            self.interaction_frame.display()

    def add_interaction_frame(self, close=True, resize=True, accept=False):
        self.interaction_frame = InteractionFrame(self)
        self.interaction_frame.set_enable_resize(True)
        self.interaction_frame.handle.signals.moved.connect(self.handle_moved)
        self.interaction_frame.handle.signals.released.connect(self.handle_released)
        self.interaction_frame.handle.signals.pressed.connect(self.handle_pressed)
        self.interaction_frame.set_enabled(close, accept, resize)

    def on_change(self, func, emit=False):
        self.swik_signals.changed.connect(func)
        if emit:
            self.swik_signals.changed.emit(self, ChangesTracker.ADDED, {})

    def handle_moved(self, event):
        pass

    def setRect(self, rect: QtCore.QRectF) -> None:
        super().setRect(rect)
        if self.interaction_frame is not None:
            self.interaction_frame.display()

    def handle_pressed(self, event):
        self.current_rect = self.rect()
        print("pressed handle", self.current_rect, self.rect(), "rects")

    def handle_released(self, event):
        if self.current_rect != self.rect():
            print("shape done")
            self.swik_signals.changed.emit(self, ChangesTracker.SHAPE_CHANGED,
                                           {'shape0': self.current_rect, 'shape1': self.rect()})

    def isMovable(self):
        return (self.flags().__int__() & 1) > 0

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseMoveEvent(event)
        if self.interaction_frame is not None:
            self.interaction_frame.display()

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mousePressEvent(event)
        self.current_pos = self.pos()
        self.current_rect = self.rect()

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)
        if self.current_pos != self.pos():
            self.swik_signals.changed.emit(self, ChangesTracker.MOVED, {'pose0': self.current_pos, 'pose1': self.pos()})
        if self.current_rect != self.rect():
            print("shape done")
            self.swik_signals.changed.emit(self, ChangesTracker.SHAPE_CHANGED, {'shape0': self.current_rect, 'shape1': self.rect()})

    def get_look(self):
        look = {'text': self.content, 'border_color': self.pen().color(), 'border_width': self.pen().width(),
                'fill_color': self.brush().color(), 'opacity': self.opacity(), 'movable': self.isMovable()}
        return look

    def die(self):
        if self.interaction_frame is not None:
            self.interaction_frame.die()

    def setMovable(self, movable):
        self.setFlag(QGraphicsItem.ItemIsMovable, movable)
        if self.interaction_frame is not None:
            self.interaction_frame.set_enable_resize(movable)

    def set_look(self, look):
        self.content = look['text']
        self.setToolTip(self.content)
        self.setMovable(look['movable'])
        self.setBrush(QBrush(look['fill_color']))
        self.setPen(QPen(look['border_color'], look['border_width']))
        self.setOpacity(look['opacity'])
