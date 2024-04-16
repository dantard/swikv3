from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QCoreApplication, Qt, QRectF, QEvent, QPoint, QThreadPool, QTimer, QMutex, QThread, \
    QRect, QPointF
from PyQt5.QtGui import QWheelEvent, QPainter, QTransform, QCursor
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QApplication, QGraphicsItem, QLabel

import utils
# import EnhancedPage
from LayoutManager import LayoutManager
from simplepage import SimplePage
from SyncDict import SyncDict
from word import Word


class GraphView(QGraphicsView):
    # ## Signals
    mouseEvent = pyqtSignal(QEvent)
    page_changed = pyqtSignal(int, int)
    processing = pyqtSignal(str, int, int)
    ratio_changed = pyqtSignal(float)
    drop_event = pyqtSignal(QtGui.QDropEvent)
    document_ready = pyqtSignal()
    page_created = pyqtSignal(SimplePage)
    page_clicked = pyqtSignal(int)

    def __init__(self, manager, renderer, scene, page=SimplePage, mode=LayoutManager.MODE_VERTICAL_MULTIPAGE):
        super().__init__()
        self.on_document_ready = []
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

        self.setScene(scene)
        self.scene().setBackgroundBrush(Qt.gray)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.get_page_size_future = None
        self.align = Qt.AlignVCenter

        # ## Connect signals
        self.renderer.document_changed.connect(self.document_changed)
        self.renderer.page_updated.connect(self.page_updated)
        self.m_layout = LayoutManager(self.renderer)


    def append_on_document_ready(self, delay, func, *args):
        print("append", (delay, func, *args))
        self.on_document_ready.append((delay, func, args))

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
            print("resize")
            scrollbar = self.horizontalScrollBar() if self.mode == LayoutManager.MODE_HORIZONTAL else self.verticalScrollBar()
            value = scrollbar.value()

            if self.fitting_width:
                self.fit_width()
            self.fully_update_layout()

            scrollbar.setValue(value)

    # ## DOCUMENT

    #    def dropEvent(self, event: QtGui.QDropEvent) -> None:
    #        self.drop_event.emit(event)

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

            if self.mode in [LayoutManager.MODE_VERTICAL, LayoutManager.MODE_VERTICAL_MULTIPAGE,
                             LayoutManager.MODE_SINGLE_PAGE]:
                percent = self.verticalScrollBar().value() / self.scene().height() if self.scene().height() != 0 else 1
            else:
                percent = self.horizontalScrollBar().value() / self.scene().width() if self.scene().width() != 0 else 1

            self.ratio = ratio

            for k, p in self.pages.items():
                p.update_image(self.get_ratio())

            self.fully_update_layout()

            if self.mode in [LayoutManager.MODE_VERTICAL, LayoutManager.MODE_VERTICAL_MULTIPAGE,
                             LayoutManager.MODE_SINGLE_PAGE]:
                self.verticalScrollBar().setValue(int(self.scene().height() * percent))
            else:
                self.horizontalScrollBar().setValue(int(self.scene().width() * percent))

        if inform:
            self.ratio_changed.emit(self.get_ratio())
        self.update()

    def set_natural_hscroll(self, value):
        self.natural_hscroll = value



    def process(self):

        # Clear all ## DO NOT change
        # the order: pages must be
        # cleaned first
        self.pages_ready = 0
        self.pages.clear()

        for item in self.scene().items():
            if hasattr(item, "die"):
                item.die()

        self.scene().clear()
        self.scene().setSceneRect(0, 0, 0, 0)
        self.m_layout.clear()

        for i in range(self.renderer.get_num_of_pages()):
            self.pages[i] = self.page_object(i, self, self.manager, self.renderer, self.get_ratio())
            self.scene().addItem(self.pages[i])

        h, v, name = self.previous_state

        if name == self.renderer.get_filename():
            self.horizontalScrollBar().setValue(h)
            self.verticalScrollBar().setValue(v)

        for delay, func, value in self.on_document_ready:
            utils.delayed(0, func, *value)

        QApplication.processEvents()
        self.fully_update_layout()


        self.on_document_ready.clear()
        #self.document_ready.emit()


    def add_annotation(self, annot):
        self.pages[annot.page].create_annotation(annot)

    def get_page(self):
        return self.page

    def get_num_of_pages(self):
        return len(self.pages)

    def get_page_count(self):
        return self.renderer.get_num_of_pages()

    def page_scrolled(self):
        max_area = 0
        for i, p in self.pages.items():  # type: SimplePage
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
        self.pages[index].page_updated(index)
        v, h = self.verticalScrollBar().value(), self.horizontalScrollBar().value()
        self.fully_update_layout()
        self.verticalScrollBar().setValue(v)
        self.horizontalScrollBar().setValue(h)

    # ## UTILITY METHODS

    def get_item_at_pos(self, pos):
        item = self.itemAt(pos)
        return item

    def get_page_at_pos(self, pos):
        item = self.items(pos)
        for i in item:
            if isinstance(i, SimplePage):
                return i
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

    def top_is(self, pos, check_items):
        items = self.scene().items(self.mapToScene(pos))
        print("Mouse pressed", items)
        if len(items) == 0:
            return False
        for item in check_items:
            if isinstance(items[0], item):
                return True
        return False

    def there_is_any_other_than(self, pos, check_items):
        items = self.scene().items(self.mapToScene(pos))
        if len(items) == 0:
            return True
        for item in items:
            if not isinstance(item, check_items):
                return True
        return False

    def over_a_page(self, event):
        if self.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return None
        else:
            return self.get_page_at_pos(event.pos())

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
        for item in reversed([p for p in self.scene().items() if type(p) == SimplePage]):
            item: SimplePage
            bounding_rect = bounding_rect.united(item.mapToScene(item.boundingRect()).boundingRect())

        self.scene().setSceneRect(bounding_rect)

    def update_layout(self, page):
        self.m_layout.update_layout(self, page)

    # ## REIMPLEMENTED METHODS
    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        try:
            self.page_scrolled()
        except Exception as e:
            pass

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
            page = self.get_items_at_pos(event.pos(), SimplePage, 0, False)
            self.set_ratio(self.get_ratio() + delta, True)

        index = self.page
        page = self.pages.get(index)

    def get_page_item(self, index):
        return self.pages[index]

    # ## SLOTS
    def document_changed(self):
        self.previous_state = (self.horizontalScrollBar().value(),
                               self.verticalScrollBar().value(),
                               self.renderer.get_filename())
        self.page_changed.emit(0, self.renderer.get_num_of_pages())
        self.process()

    def set_page(self, index):
        self.move_to_page(index)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        print("View mouse pressed")
        super().mousePressEvent(event)
        self.manager.mouse_pressed(event)
        page = self.get_items_at_pos(event.pos(), SimplePage, 0, False)
        if page is not None:
            self.page_clicked.emit(page.index)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self.manager.mouse_released(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        self.manager.mouse_moved(event)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        super().contextMenuEvent(event)
        if not event.isAccepted():
            self.manager.context_menu(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseDoubleClickEvent(event)
        self.manager.mouse_double_clicked(event)

    def rearrange(self, indices):
        # self.renderer.rearrange_pages(indices, False)
        class Element:
            def __init__(self, page, count=0):
                self.page = page
                self.count = count
                self.prev_pos = page.index
                self.current_pos = page.index

        buffer = []

        for page in self.pages.values():
            buffer.append(Element(page))
        self.pages.clear()

        for i in range(len(indices)):
            elem = buffer[indices[i]]
            if elem.count == 0:
                print("page", i, "copy")
                self.pages[i] = elem.page
                self.pages[i].index = i
            else:
                # Going to duplicate the page
                print("page", i, "create")
                page = self.page_object(i, self, self.manager, self.renderer, self.ratio)
                self.finish_setup(page)
                self.pages[i] = page
            elem.current_pos = i
            elem.count += 1

        for elem in buffer:
            if elem.count == 0:
                self.scene().removeItem(elem.page)
            elif elem.current_pos != elem.prev_pos:
                elem.page.invalidate()

    def append_blank_page(self):
        last_page = len(self.pages)
        page = self.page_object(last_page, self, self.manager, self.renderer, self.ratio)
        self.finish_setup(page)
        self.pages[last_page] = page
        return last_page
