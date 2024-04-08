from PyQt5.QtCore import QObject, pyqtSignal, Qt, QRectF, QUrl, QPointF
from PyQt5.QtGui import QDesktopServices, QColor
from PyQt5.QtWidgets import QGraphicsRectItem


class Link(QGraphicsRectItem):
    class Signals(QObject):
        clicked = pyqtSignal(int, QPointF)

    def __init__(self, rect: QRectF, page):
        super().__init__(rect, page)
        self.signals = Link.Signals()
        self.setBrush(QColor(0, 0, 255, 0))


class ExternalLink(Link):
    def __init__(self,  rect, page,  uri):
        super().__init__(rect, page)
        self.uri = uri
        self.setPen(Qt.red)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super(Link, self).mousePressEvent(event)
        QDesktopServices.openUrl(QUrl(self.uri))


class InternalLink(Link):
    def __init__(self,  rect, page, dest):
        super().__init__(rect, page)
        self.dest_page = dest[0]
        self.x = dest[1]
        self.y = dest[2]
        self.setPen(Qt.blue)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super(Link, self).mousePressEvent(event)
        self.signals.clicked.emit(self.dest_page, QPointF(self.x, self.y))

