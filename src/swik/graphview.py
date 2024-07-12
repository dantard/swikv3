from multiprocessing.pool import ThreadPool

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QCoreApplication, Qt, QEvent, QPoint, QTimer, QMutex, QRectF
from PyQt5.QtGui import QWheelEvent, QPainter, QColor
from PyQt5.QtWidgets import QGraphicsView, QGraphicsRectItem, QApplication, QScrollBar, QGraphicsEllipseItem

from swik import utils
from swik.annotations.hyperlink import InternalLink
# import EnhancedPage
from swik.layout_manager import LayoutManager
from swik.sync_dict import SyncDict
from swik.simplepage import SimplePage
from swik.word import Word


class SB(QScrollBar):
    pass


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

    def __init__(self, manager, renderer, scene, page=SimplePage, mode=LayoutManager.MODE_VERTICAL_MULTIPAGE, align=Qt.AlignVCenter | Qt.AlignHCenter,
                 page_sep=27):
        super().__init__()
        self.on_document_ready = []
        self.previous_state = 0, 0, None
        self.page_object = page
        self.ratio = 1
        self.natural_hscroll = False
        self.renderer = renderer
        self.manager = manager
        self.page = 0
        self.mode = mode
        self.pages = SyncDict()
        self.immediate_resize = False

        self.setScene(scene)
        self.scene().setBackgroundBrush(Qt.gray)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.align = Qt.AlignVCenter
        self.setVerticalScrollBar(SB())
        # ## Connect signals
        # self.renderer.document_changed.connect(self.document_changed)
        self.renderer.page_updated.connect(self.page_updated)
        self.layout_manager = LayoutManager(self, self.renderer, mode, align, page_sep)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.delayed_resize)
        self.hhh = QGraphicsRectItem()
        self.hhh.setBrush(QColor(10, 10, 10, 255))
        self.hhh.setPos(0, 0)
        self.scene().addItem(self.hhh)

    def set_mode(self, mode, force=False):
        print("Setting mode", mode, force)
        self.mode = mode
        self.layout_manager.set_mode(mode, force)
        if mode == LayoutManager.MODE_FIT_WIDTH:
            self.ratio_changed.emit(-1)

    def finish(self):
        self.pages.clear()

    def get_mode(self):
        return self.layout_manager.get_mode()

    def set_one_shot_immediate_resize(self):
        self.immediate_resize = True

    # ## EVENTS
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.timer.stop()
        if event.oldSize().width() != event.size().width():
            if self.immediate_resize:
                self.delayed_resize()
                self.immediate_resize = False
            else:
                self.timer.start(50)

    def delayed_resize(self):
        scrollbar = self.horizontalScrollBar() if self.mode == LayoutManager.MODE_HORIZONTAL else self.verticalScrollBar()
        value = scrollbar.value()
        #        self.fully_update_layout2()
        self.layout_manager.fully_update_layout()
        scrollbar.setValue(value)

    # ## DOCUMENT

    #    def dropEvent(self, event: QtGui.QDropEvent) -> None:
    #        self.drop_event.emit(event)

    def get_width(self):
        return self.geometry().width()

    def get_ratio(self):
        return self.ratio

    def set_ratio(self, ratio, inform=False):
        if self.layout_manager.get_mode() == LayoutManager.MODE_FIT_WIDTH:
            self.layout_manager.set_mode(LayoutManager.MODE_VERTICAL, False)

        ratio = min(max(self.layout_manager.ratio_min, ratio), self.layout_manager.ratio_max)

        # Record radio change
        self.ratio = ratio

        if self.layout_manager.is_vertical():
            percent = self.verticalScrollBar().value() / self.scene().height() if self.scene().height() != 0 else 1
        else:
            percent = self.horizontalScrollBar().value() / self.scene().width() if self.scene().width() != 0 else 1

        self.layout_manager.reset()

        if self.layout_manager.is_vertical():
            self.verticalScrollBar().setValue(int(self.scene().height() * percent))
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().maximum() / 2))
        else:
            self.horizontalScrollBar().setValue(int(self.scene().width() * percent))

        for page in self.pages.values():
            page.update_image(self.ratio)
            self.layout_manager.update_layout(page)

        if inform:
            self.ratio_changed.emit(self.get_ratio())
        self.scene().setBackgroundBrush(Qt.gray)

    def set_natural_hscroll(self, value):
        self.natural_hscroll = value

    def clear(self):
        self.pages.clear()
        self.scene().clear()

    def create_page(self, i):
        self.pages[i] = self.page_object(i, self, self.manager, self.renderer, self.get_ratio())
        self.scene().addItem(self.pages[i])
        return self.pages[i]

    def get_page(self):
        return self.page

    def get_scroll_value(self):
        if self.layout_manager.mode in [LayoutManager.MODE_VERTICAL, LayoutManager.MODE_VERTICAL_MULTIPAGE, LayoutManager.MODE_SINGLE_PAGE]:
            return self.verticalScrollBar().value()
        else:
            return self.horizontalScrollBar().value()

    def set_scroll_value(self, value):
        if self.layout_manager.mode in [LayoutManager.MODE_VERTICAL, LayoutManager.MODE_VERTICAL_MULTIPAGE, LayoutManager.MODE_SINGLE_PAGE]:
            self.verticalScrollBar().setValue(value)
        else:
            self.horizontalScrollBar().setValue(value)

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

    def move_to_page(self, index, offset=None):
        print("move to page", index, offset, self.pages.get(index))
        if (page := self.pages.get(index)) is not None:
            offset = -10 if offset is None else offset

            self.page = index
            self.layout_manager.move_to_page(page)

            # Must be here because of the fit_width that changes the scrollbars
            if self.mode in [LayoutManager.MODE_VERTICAL_MULTIPAGE, LayoutManager.MODE_VERTICAL]:
                print("SCROLLING", page.pos().y(), offset, self.get_ratio())
                self.verticalScrollBar().setValue(int((page.pos().y() + offset * self.get_ratio())))
            else:
                self.horizontalScrollBar().setValue(int((page.pos().x() + offset * self.get_ratio())))

            page.update()
            self.page_changed.emit(index, self.renderer.get_num_of_pages())

    def page_updated(self, index):
        self.pages[index].invalidate()
        v, h = self.verticalScrollBar().value(), self.horizontalScrollBar().value()

        QApplication.processEvents()

        self.layout_manager.fully_update_layout()
        self.verticalScrollBar().setValue(v)
        self.horizontalScrollBar().setValue(h)

    # ## UTILITY METHODS

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
            if self.mode in LayoutManager.Vertical:
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
            delta = int((event.angleDelta().y() / 1200) * 100) / 100
            mouse_on_scene = self.mapToScene(event.pos())
            page = self.get_items_at_pos(event.pos(), SimplePage, 0, False)
            self.set_ratio(self.get_ratio() + delta, True)

        index = self.page
        page = self.pages.get(index)

    def get_page_item(self, index):
        return self.pages[index]

    # ## SLOTS

    def update_layout(self):
        self.layout_manager.fully_update_layout()

    def set_page(self, index):
        self.move_to_page(index)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        # print("View mouse pressed")
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
                # print("page", i, "copy")
                self.pages[i] = elem.page

                if self.pages[i].index != i:
                    self.pages[i].shine()

                self.pages[i].index = i

            else:
                # Going to duplicate the page
                # print("page", i, "create")
                page = self.page_object(i, self, self.manager, self.renderer, self.ratio)
                page.update_original_info({"page": "+"})
                page.update_image(self.ratio)
                self.pages[i] = page
                self.scene().addItem(page)
                page.shine(QColor(255, 0, 0, 100))

            elem.current_pos = i
            elem.count += 1

        for elem in buffer:
            if elem.count == 0:
                self.scene().removeItem(elem.page)
            elif elem.current_pos != elem.prev_pos:
                elem.page.invalidate()

    def insert_page(self, index):
        pages = {}
        for i in range(len(self.pages) + 1):
            if i < index:
                pages[i] = self.pages[i]
            elif i == index:
                pages[i] = self.page_object(index, self, self.manager, self.renderer, self.get_ratio())
                pages[i].update_original_info({"page": "+"})
                pages[i].update_image(self.ratio)
                self.scene().addItem(pages[i])
                pages[i].shine(QColor(255, 0, 0, 100))
            else:
                pages[i] = self.pages[i - 1]
                pages[i].index = i

        self.pages = pages
        return self.pages[index]
