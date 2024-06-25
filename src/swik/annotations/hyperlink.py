from PyQt5.QtCore import QObject, pyqtSignal, Qt, QRectF, QUrl, QPointF
from PyQt5.QtGui import QDesktopServices, QColor
from PyQt5.QtWidgets import QGraphicsRectItem


class Link(QGraphicsRectItem):
    class Signals(QObject):
        clicked = pyqtSignal(int, QPointF)
        link_hovered = pyqtSignal(int, int, QPointF)

    ENTER, MOVE, LEAVE = 0, 1, 2

    def __init__(self, rect: QRectF, page):
        super().__init__(QRectF(0,0,rect.width(), rect.height()), page)
        self.signals = Link.Signals()
        self.setBrush(QColor(0, 0, 255, 0))
        self.setPos(rect.x(), rect.y())
        self.page = page


class ExternalLink(Link):
    def __init__(self, rect, page, uri):
        super().__init__(rect, page)
        self.uri = uri
        self.setPen(Qt.red)
        self.setAcceptHoverEvents(True)


    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super(Link, self).mousePressEvent(event)
        QDesktopServices.openUrl(QUrl(self.uri))

    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.setCursor(Qt.PointingHandCursor)

    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.setCursor(Qt.ArrowCursor)

class InternalLink(Link):
    def __init__(self, rect, page, dest):
        super().__init__(rect, page)
        self.dest_page = dest[0]
        self.x = dest[1]
        self.y = dest[2]
        self.setPen(Qt.blue)
        self.setAcceptHoverEvents(True)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super(Link, self).mousePressEvent(event)
        pos = self.page.mapToScene(QPointF(self.x, self.y))
        self.signals.clicked.emit(self.dest_page, QPointF(self.x, self.y))

    def hoverMoveEvent(self, event):
        super().hoverMoveEvent(event)
        self.signals.link_hovered.emit(Link.MOVE, self.dest_page, QPointF(self.x, self.y))

    def hoverEnterEvent(self, event):
        self.signals.link_hovered.emit(Link.ENTER, self.dest_page, QPointF(self.x, self.y))
        self.setCursor(Qt.PointingHandCursor)

    def hoverLeaveEvent(self, event):
        self.signals.link_hovered.emit(Link.LEAVE, self.dest_page, QPointF(self.x, self.y))
        self.setCursor(Qt.ArrowCursor)