from PyQt5 import QtCore
from PyQt5.QtWidgets import QMenu

from annotations.annotation import Annotation


class SquareAnnotation(Annotation):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        menu = QMenu("Square Annotation")
        menu.addAction("Edit", self.change_color)
        menu.addSeparator()
        delete = menu.addAction("Delete")
        res = menu.exec(event.screenPos())
        if res == delete:
            self.notify_deletion(self)
            self.scene().removeItem(self)
