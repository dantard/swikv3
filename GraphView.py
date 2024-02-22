from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QCoreApplication, Qt, QRectF, QEvent, QPoint, QThreadPool, QTimer, QMutex, QThread, \
    QRect, QPointF
from PyQt5.QtGui import QWheelEvent, QPainter, QTransform, QCursor
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QApplication, QGraphicsItem, QLabel

# import EnhancedPage
from LayoutManager import LayoutManager
from Page import Page
from SyncDict import SyncDict


class GraphView(QGraphicsView):
    # ## Signals
    mouseEvent = pyqtSignal(QEvent)
    page_changed = pyqtSignal(int, int)
    processing = pyqtSignal(str, int, int)
    ratio_changed = pyqtSignal(float)
    drop_event = pyqtSignal(QtGui.QDropEvent)
    document_ready = pyqtSignal()
    page_created = pyqtSignal(Page)

    def __init__(self, manager, renderer, mode, page=Page):
        super().__init__()
        self.previous_state = 0, 0, None
        self.page_object = page
        self.scrolled = pyqtSignal(QWheelEvent)
        self.ratio = 1
        self.pages_ready = 0
        self.pages_ready_mtx = QMutex()
        self.natural_hscroll = False
        self.renderer = renderer
        self.manager = manager
        self.fitting_width = False
        self.exiting = False
        self.page = 0
        self.mode = mode
        self.pages = SyncDict()
        self.futures = list()

        class MyScene(QGraphicsScene):
            class Signals(QtCore.QObject):
                item_added = pyqtSignal(QGraphicsItem)
                item_removed = pyqtSignal(QGraphicsItem)

            def __init__(self):
                super().__init__()
                self.signals = self.Signals()

            def addItem(self, item) -> None:
                super().addItem(item)
                self.signals.item_added.emit(item)

            def removeItem(self, item) -> None:
                super().removeItem(item)
                self.signals.item_removed.emit(item)

        self.setScene(MyScene())
        self.scene().setBackgroundBrush(Qt.gray)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.get_page_size_future = None
        self.align = Qt.AlignVCenter

        # ## Connect signals
        self.renderer.document_changed.connect(self.document_changed)
        self.renderer.page_updated.connect(self.page_updated)
        self.m_layout = LayoutManager(self.renderer)
        self.tpe = ThreadPoolExecutor(1)
        self.page_created.connect(self.page_processed)

    #        self.qtimer = QTimer()
    #        self.qtimer.timeout.connect(lambda: print(self.tpe._work_queue.qsize()))
    #        self.qtimer.start(10)
    # ## CHANGE CONFIG
    def set_mode(self, mode, force=False):
        if mode != self.mode or force:
            self.mode = mode
            self.fully_update_layout()

    def finish(self):
        self.pages.clear()

    def set_alignment(self, align):
        self.align = align

    def get_mode(self):
        return self.mode

    # ## EVENTS
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        if event.oldSize().width() != event.size().width():

            scrollbar = self.horizontalScrollBar() if self.mode == LayoutManager.MODE_HORIZONTAL else self.verticalScrollBar()
            value = scrollbar.value()

            if self.fitting_width:
                self.fit_width()
            self.fully_update_layout()

            scrollbar.setValue(value)

    # ## DOCUMENT

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        self.drop_event.emit(event)

    def get_width(self):
        return self.geometry().width()

    def get_page_width(self, index):
        return self.pages[index].get_orig_width()

    def set_fit_width(self, value):
        self.fitting_width = value
        if value:
            self.fit_width()

    def fit_width(self):
        for page in self.pages.values():
            page.fit_width()
        self.fully_update_layout()

    def is_fitting_width(self):
        return self.fitting_width

    def get_ratio(self):
        return self.ratio

    def get_thread_pool(self):
        return self.tpe

    def set_ratio(self, ratio, inform=False):
        ratio = min(max(self.m_layout.ratio_min, ratio), self.m_layout.ratio_max)
        if round(ratio, 2) != round(self.get_ratio(), 2):

            if self.mode in [LayoutManager.MODE_VERTICAL, LayoutManager.MODE_VERTICAL_MULTIPAGE, LayoutManager.MODE_SINGLE_PAGE]:
                percent = self.verticalScrollBar().value() / self.scene().height() if self.scene().height() != 0 else 1
            else:
                percent = self.horizontalScrollBar().value() / self.scene().width() if self.scene().width() != 0 else 1

            self.ratio = ratio

            for k, p in self.pages.items():
                p.update_image(self.get_ratio())

            self.fully_update_layout()

            if self.mode in [LayoutManager.MODE_VERTICAL, LayoutManager.MODE_VERTICAL_MULTIPAGE, LayoutManager.MODE_SINGLE_PAGE]:
                self.verticalScrollBar().setValue(int(self.scene().height() * percent))
            else:
                self.horizontalScrollBar().setValue(int(self.scene().width() * percent))

        if inform:
            self.ratio_changed.emit(self.get_ratio())
        self.update()

    def set_natural_hscroll(self, value):
        self.natural_hscroll = value

    def page_processed(self, page):
        assert (isinstance(page, Page))
        page.connect_signals()
        page.finish_setup()
        self.scene().addItem(page)
        # print("page processed ****** ", page.index)
        self.update_layout(page)

        # self.page_changed.emit(0, self.renderer.get_num_of_pages())

        # Check if this was the last thread and emit signals
        # Do it with mutex to avoid wrong increment of thread_count
        self.pages_ready_mtx.lock()
        # print("Done creating page", page.index, self.pages_ready)
        self.pages_ready += 1

        #        print("emitting", self.pages_ready, type(self))
        self.processing.emit('Pages', self.pages_ready, self.renderer.get_num_of_pages())

        if self.pages_ready == self.renderer.get_num_of_pages():
            h, v, name = self.previous_state
            # print("emitting document ready", h, v)
            if name == self.renderer.get_filename():
                self.horizontalScrollBar().setValue(h)
                self.verticalScrollBar().setValue(v)
            self.document_ready.emit()

        self.pages_ready_mtx.unlock()

    def process(self):
        print("PROCESSING*******************", self.pages_ready, type(self))

        # Cancel all the threads that may
        # still be running and creating pages
        for f in self.futures:  # type: Future
            if not f.done():
                f.cancel()

        # Clear all ## DO NOT change
        # the order: pages must be
        # cleaned first
        self.pages_ready = 0
        self.pages.clear()
        self.futures.clear()
        for item in self.scene().items():
            if hasattr(item, "die"):
                item.die()

        self.scene().clear()
        self.scene().setSceneRect(0, 0, 0, 0)
        self.m_layout.clear()
        # self.ratio = 1
        # self.get_page_size_future = self.tpe.submit(self.m_layout.update_pages_size)
        self.create_pages(None)
        # self.get_page_size_future.add_done_callback(self.create_pages)

    def do_create_page(self, index):
        # In the Constructor page gets also its size itself
        p = self.page_object(index, self, self.manager, self.renderer, self.get_ratio())
        # print("TYPE", self.page_object, p)
        assert (isinstance(p, Page))

        self.pages[index] = p

        # Wait for the page size to be obtained
        # This is needed for the update_layout to work
        # self.get_page_size_future.result()

        # OK ready to finish the page setup
        self.page_created.emit(p)

    def create_pages(self, future):
        # print("PROCESSING2*******************", self.pages_ready, type(self), len(self.futures))

        unthreaded = min(50, self.renderer.get_num_of_pages())

        for i in range(unthreaded):
            print("Creating unthreaded page", i)
            self.do_create_page(i)

        QApplication.processEvents()

        for i in range(unthreaded, self.renderer.get_num_of_pages()):
            print("Creating threaded page", i)
            self.futures.append(self.tpe.submit(self.do_create_page, i))

    def add_annotation(self, annot):
        self.pages[annot.page].create_annotation(annot)

    def get_page(self):
        return self.page

    def get_num_of_pages(self):
        return len(self.pages)

    def page_scrolled(self):
        max_area = 0
        for i, p in self.pages.items():  # type: Page
            area, isec = p.visible_area()
            if area > max_area:
                max_area = area
                self.page = i
            if max_area > 0 and area == 0:
                break
            # if p.isShown():
            #    self.page = i
            #    break
        self.page_changed.emit(self.page, self.renderer.get_num_of_pages())

    def get_current_page(self):
        return self.pages.get(self.page)

    def get_page_offset(self, index):
        page = self.pages.get(index)
        return -self.mapFromScene(page.scenePos()).y()

    def move_to_page(self, index, offset=None):
        # print("move to page")
        if (page := self.pages.get(index)) is not None:
            offset = -10 if offset is None else offset

            self.page = index

            if self.mode == LayoutManager.MODE_SINGLE_PAGE:
                self.fully_update_layout()

            if self.fitting_width:
                self.fit_width()

            # Must be here because of the fit_width that changes the scrollbars
            if self.mode in [LayoutManager.MODE_VERTICAL_MULTIPAGE, LayoutManager.MODE_VERTICAL]:
                print("SCROLLING", page.pos().y(), offset, self.get_ratio())
                self.verticalScrollBar().setValue(int((page.pos().y() + offset * self.get_ratio())))
            else:
                self.horizontalScrollBar().setValue(int((page.pos().x() + offset * self.get_ratio())))

            page.update()
        # self.page_changed.emit(index, self.renderer.get_num_of_pages())

    def set_override_cursor(self, cursor):
        self.viewport().setCursor(cursor)

    def reset_cursor(self):
        self.viewport().setCursor(Qt.ArrowCursor)

    def page_updated(self, index):
        v, h = self.verticalScrollBar().value(), self.horizontalScrollBar().value()
        self.fully_update_layout()
        self.verticalScrollBar().setValue(v)
        self.horizontalScrollBar().setValue(h)

    # ## UTILITY METHODS

    def get_item_at_pos(self, pos):
        item = self.itemAt(pos)
        return item

    def get_page_at_pos(self, pos):
        item = self.itemAt(pos)
        if item is not None:
            if not isinstance(item, Page):
                item = item.parentItem()
                if not isinstance(item, Page):
                    item = item.parentItem()
            return item
        return None

    # Get items at specific point, It is possible to filter
    # by Item type and index
    def get_items_at_pos(self, point, kind=None, index=-1, strict=True):
        items = self.items(point)
        if kind is None:
            return items if len(items) > 0 else None
        else:
            if strict:
                items_of_type_kind = [it for it in items if type(it) == kind]
            else:
                items_of_type_kind = [it for it in items if isinstance(it, kind)]

            if len(items_of_type_kind) == 0:
                return None
            elif index == -1:
                return items_of_type_kind
            elif 0 <= index < len(items_of_type_kind):
                return items_of_type_kind[index]
            else:
                return None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def get_page_at_global(self, pos: QPoint):
        pos = self.mapFromGlobal(pos)
        return self.get_page_at_pos(pos).index

    def fully_update_layout(self):

        self.m_layout.clear()
        for i in range(self.renderer.get_num_of_pages()):
            if (p := self.pages.get(i)) is not None:
                self.update_layout(p)

        self.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        self.setAlignment(self.align | Qt.AlignHCenter)

        if self.mode != LayoutManager.MODE_HORIZONTAL:
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().maximum() / 2))
        else:
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().maximum() / 2))

        # print("fully done", type(self))

    def resize_scene(self):
        bounding_rect = QRectF()
        for item in reversed([p for p in self.scene().items() if type(p) == Page]):
            item: Page
            bounding_rect = bounding_rect.united(item.mapToScene(item.boundingRect()).boundingRect())

        self.scene().setSceneRect(bounding_rect)

    def update_layout(self, page):
        self.m_layout.update_layout(self, page)

    # ## REIMPLEMENTED METHODS
    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self.page_scrolled()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers != QtCore.Qt.ControlModifier:
            if self.mode in [LayoutManager.MODE_VERTICAL,
                             LayoutManager.MODE_VERTICAL_MULTIPAGE,
                             LayoutManager.MODE_SINGLE_PAGE]:
                super().wheelEvent(event)
            else:
                modifiers = QtWidgets.QApplication.keyboardModifiers()
                if not self.natural_hscroll:
                    if modifiers == QtCore.Qt.ShiftModifier:
                        super().wheelEvent(event)
                    else:
                        QCoreApplication.sendEvent(self.horizontalScrollBar(), event)
                else:
                    if modifiers == QtCore.Qt.ShiftModifier:
                        QCoreApplication.sendEvent(self.horizontalScrollBar(), event)
                    else:
                        super().wheelEvent(event)
        else:
            # if not self.fitting_width:
            self.fitting_width = False
            delta = int((event.angleDelta().y() / 1200) * 100) / 100
            mouse_on_scene = self.mapToScene(event.pos())
            page = self.get_items_at_pos(event.pos(), Page, 0, False)
            print("ababab", self.horizontalScrollBar().value(), self.scene().width())
            self.set_ratio(self.get_ratio() + delta, True)

        index = self.page
        page = self.pages.get(index)
        print(index, page.scenePos().y(), page.pos().y(), self.mapFromScene(page.scenePos()).y())

    def get_page_item(self, index):
        return self.view.pages[index]

    # ## SLOTS
    def document_changed(self):
        self.previous_state = (self.horizontalScrollBar().value(),
                               self.verticalScrollBar().value(),
                               self.renderer.get_filename())

        self.process()

    def set_page(self, index):
        self.move_to_page(index)


class MiniatureView(GraphView):
    page_clicked = pyqtSignal(int, int)

    def __init__(self, renderer, mode, page):
        super(MiniatureView, self).__init__(renderer, mode, page)

    def wheelEvent(self, event: 'QGraphicsSceneWheelEvent') -> None:
        super(QGraphicsView, self).wheelEvent(event)

    def set_page(self, index):
        for p in self.pages.values():
            p.box.setVisible(False)

        if self.pages.get(index) is not None:
            self.pages[index].box.setVisible(True)
            if not self.pages[index].is_completely_shown():
                self.ensureVisible(self.pages[index], 0, 50)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            page = self.get_items_at_pos(event.pos(), Page, 0, False)
            if page is not None:
                self.pages[self.page].box.setVisible(False)
                self.page_clicked.emit(page.index, self.renderer.get_num_of_pages())
                self.pages[page.index].box.setVisible(True)

# def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
#     QGraphicsView.wheelEvent(self, event)
