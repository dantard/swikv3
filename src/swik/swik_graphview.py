from PyQt5.QtCore import pyqtSignal, QRectF, Qt, QTimer, QPoint
from PyQt5.QtGui import QColor, QCursor, QHoverEvent, QPainter, QTransform
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsView, QPushButton

import swik.utils as utils
from swik.graphview import GraphView
from swik.layout_manager import LayoutManager
from swik.annotations.highlight_annotation import HighlightAnnotation
from swik.annotations.hyperlink import InternalLink
from swik.annotations.redact_annotation import RedactAnnotation
from swik.annotations.square_annotation import SquareAnnotation
from swik.bunch import NumerateBunch
from swik.page import Page
from swik.simplepage import SimplePage
from swik.swik_text import SwikText, SwikTextReplace, SwikTextNumerate
from swik.tools.tool_insert_image import InsertImageRectItem
from swik.widgets.pdf_widget import PdfWidget


class Shower(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.close = QPushButton("✕")
        self.close.setParent(self)
        self.close.clicked.connect(self.hide)
        self.pin = QPushButton("•")
        self.pin.setParent(self)
        self.pin.setCheckable(True)
        self.setAttribute(Qt.WA_Hover, True)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.bury)

        self.timer2 = QTimer()
        self.timer2.setSingleShot(True)
        self.timer2.timeout.connect(self.show_link)

        self.pos1 = None
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        # self.link_shower.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        # self.setTransform(QTransform().scale(0.5, 0.5))
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

    def setPoseSize(self, x, y, w, h):
        if self.pin.isChecked():
            self.setGeometry(self.geometry().x(), self.geometry().y(), w, h)
        else:
            self.setGeometry(x, y, w, h)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.pos1 = event.pos()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.pos1 is not None:
            self.move(event.globalPos() - self.pos1)

    def mouseReleaseEvent(self, event):
        self.pos1 = None

    def show(self):
        super().show()
        self.timer.start(1500)

    def event(self, event):
        if event.type() == QHoverEvent.HoverEnter:
            self.timer.stop()
        if event.type() == QHoverEvent.HoverLeave:
            self.bury()
        return super().event(event)

    def resizeEvent(self, event):
        self.close.setGeometry(self.width() - 40, 10, 20, 20)
        self.pin.setGeometry(self.width() - 65, 10, 20, 20)
        super().resizeEvent(event)

    def bury(self):
        if not self.pin.isChecked():
            self.hide()

    def hoverLeaveEvent(self, event):
        QTimer.singleShot(100, self.bury)

    def enter(self, page, pos):
        self.page = page
        self.pos = self.page.mapToScene(pos)
        self.timer2.start(1000)

    def leave(self, page, pos):
        self.timer2.stop()

    def show_link(self):
        self.setSceneRect(0, self.pos.y() - 600, self.page.sceneBoundingRect().width(), 1200)
        self.setPoseSize(QCursor.pos().x() + 5, QCursor.pos().y() + 20, int(self.page.sceneBoundingRect().width()), 400)
        self.verticalScrollBar().setValue(int(self.pos.y()))
        self.show()


class Magnifier(QGraphicsView):

    def __init__(self, scene, main_view):
        super().__init__(scene)
        self.main_view: QGraphicsView = main_view
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # self.link_shower.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setTransform(QTransform().scale(2, 2))
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.close = QPushButton("✕")
        self.close.setParent(self)
        self.close.setGeometry(10, 10, 20, 20)
        self.close.clicked.connect(self.hide)

        self.plus = QPushButton("+")
        self.plus.setParent(self)
        self.plus.setGeometry(30, 10, 20, 20)

        self.minus = QPushButton("-")
        self.minus.setParent(self)
        self.minus.setGeometry(60, 10, 20, 20)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.pos1 = event.pos()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.pos1 is not None:
            self.move(event.globalPos() - self.pos1)

        print("pose1", self.pos())
        obj = self.main_view
        pose = QPoint(0, 0)
        while obj is not None:
            pose += obj.mapToParent(QPoint(0, 0))
            obj = obj.parent()

        pose = self.pos() - pose

        # print("pose2", pose)
        pose = self.main_view.mapToScene(pose)
        print("pose3", pose)
        self.setSceneRect(pose.x(), pose.y(), 200, 200)
        self.setFixedSize(400, 400)

    def mouseReleaseEvent(self, event):
        self.pos1 = None


class SwikGraphView(GraphView):
    drop_event = pyqtSignal(list)

    def __init__(self, manager, renderer, scene, page=SimplePage, mode=LayoutManager.MODE_VERTICAL_MULTIPAGE):
        super(SwikGraphView, self).__init__(manager, renderer, scene, page, mode)
        self.renderer.sync_requested.connect(self.sync_requested)
        self.renderer.sync_dynamic.connect(self.sync_dynamic)
        self.setAcceptDrops(True)
        self.link_shower = Shower(self.scene())

    def dropEvent(self, event) -> None:
        event.accept()
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = []
            for url in urls:
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
            if len(paths) > 0:
                self.drop_event.emit(paths)

    def dragEnterEvent(self, event) -> None:
        event.accept()

    def dragMoveEvent(self, event) -> None:
        event.accept()

        # Here you can process the file path as needed

    def sync_dynamic(self):
        items = self.scene().items()
        pages_to_refresh = set()

        square_annot = [item for item in items if type(item) == SquareAnnotation]
        for annot in square_annot:  # type: RedactAnnotation
            page: Page = annot.parentItem()
            self.renderer.add_annot(page.get_index(), annot)

        highlight_annot = [item for item in items if type(item) == HighlightAnnotation]
        for annot in highlight_annot:
            page: Page = annot.parentItem()
            self.renderer.add_highlight_annot(page.index, annot)
            pages_to_refresh.add(page.get_index())

        for index in pages_to_refresh:
            self.pages[index].invalidate()

    def sync_requested(self):
        items = self.scene().items()
        pages_to_refresh = set()

        redact_annot = [item for item in items if type(item) == RedactAnnotation]
        for annot in redact_annot:  # type: RedactAnnotation
            page: Page = annot.parentItem()
            self.renderer.add_redact_annot(page.index, annot.get_rect_on_parent(), annot.brush().color())
            pages_to_refresh.add(page.index)
            self.scene().removeItem(annot)

        swik_text = [item for item in items if type(item) == SwikText]
        for text in swik_text:
            page: Page = text.parentItem()
            self.renderer.add_text(page.get_index(), text)
            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(text)

        swik_text_replace = [item for item in items if type(item) == SwikTextReplace]
        for text in swik_text_replace:
            page: Page = text.parentItem()
            self.renderer.replace_word(page.get_index(), text)
            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(text)

        swik_text_numerate = [item for item in items if type(item) == SwikTextNumerate]
        for text in swik_text_numerate:
            page: Page = text.parentItem()
            self.renderer.add_text(page.get_index(), text)
            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(text)
        self.scene().remove_bunches(NumerateBunch)

        images = [item for item in items if isinstance(item, InsertImageRectItem)]
        for image in images:
            page: Page = image.parentItem()
            self.renderer.insert_image_from_file(page.get_index(), image.get_image_rect_on_parent(),
                                                 image.get_image_filename())
            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(image)

        for index in pages_to_refresh:
            self.pages[index].invalidate()

    def create_page(self, page, ratio=1):
        page = super().create_page(page)
        page.update_image(ratio)
        return page

    def link_hovered(self, kind, page, pos):

        dest_page = self.pages[page]

        if kind == InternalLink.ENTER:
            self.link_shower.enter(dest_page, pos)


        elif kind == InternalLink.LEAVE:
            self.link_shower.leave(dest_page, pos)

    def link_clicked(self, page, pos):
        # self.move_to_page(page)
        ellipse = QGraphicsEllipseItem(QRectF(0, 0, 10, 10), self.pages[page])
        ellipse.setBrush(QColor(255, 0, 0, 255))
        ellipse.setPen(Qt.transparent)
        ellipse.setPos(pos)
        self.centerOn(ellipse)
        utils.delayed(2000, self.scene().removeItem, ellipse)

    def toggle_page_info(self):
        for page in self.pages.values():
            page.toggle_info()
