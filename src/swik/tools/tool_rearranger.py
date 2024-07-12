from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtWidgets import QGraphicsRectItem, QMenu, QFileDialog, QMessageBox, QVBoxLayout, QWidget, QPushButton, QApplication, QGraphicsView
from pymupdf import Page

from swik.progressing import Progressing

from swik import utils

from swik.action import Action
from swik.interfaces import Undoable
from swik.selector import SelectorRectItem
from swik.simplepage import SimplePage
from swik.tools.tool import Tool


def move_numbers(vector, numbers_to_move, position):
    # Remove the selected numbers from the vector
    for number in numbers_to_move:
        vector.remove(number)

    position, side = position

    # Find the index where to insert the numbers
    insert_index = vector.index(position)
    insert_index = insert_index + 1 if side == 1 else insert_index

    # Insert the numbers at the specified position
    for number in reversed(numbers_to_move):
        vector.insert(insert_index, number)

    return vector


class ToolRearrange(Tool, Undoable):
    STATE_RECT_SELECTION = 0
    STATE_PAGE_SELECTION = 1
    STATE_PAGE_MOVING = 2

    def __init__(self, widget):
        super().__init__(widget)
        self.selected = []
        self.pickup_point = None
        self.leader_page = None
        self.collider = None
        self.insert_at_page = None
        self.state = None
        self.orig_ratio = None
        self.rb = None
        self.views = [self.view] + widget.get_other_views()
        self.append_id = 0

    def init(self):
        self.collider = QGraphicsRectItem()
        self.collider.setBrush(QColor(0, 255, 0, 128))
        self.collider.setPen(Qt.transparent)
        self.collider.setVisible(False)
        self.view.scene().addItem(self.collider)
        self.orig_ratio = self.view.get_ratio()
        self.view.set_ratio(0.25, True)

        v_layout = QVBoxLayout()
        self.helper = QWidget()
        self.helper.setLayout(v_layout)
        self.append_btn = QPushButton("Append PDF")
        self.show_numbers_btn = QPushButton("Show Info")
        self.show_numbers_btn.setCheckable(True)
        self.show_numbers_btn.clicked.connect(self.show_numbers)

        self.append_btn.clicked.connect(self.append_pdf)
        v_layout.addWidget(self.append_btn)
        v_layout.addWidget(self.show_numbers_btn)

        self.widget.set_app_widget(self.helper, 150, title="Rearrange")

        for page in self.view.pages.values():
            page.update_original_info({"append_id": self.append_id})

    def show_numbers(self):
        for page in self.view.pages.values():
            info = page.get_original_info()
            page.set_visual_info("{}".format(info.get("page", "")), utils.get_color(info.get("append_id", 0)))
            page.show_visual_info(self.show_numbers_btn.isChecked())

    def append_pdf(self):

        filename, _ = QFileDialog.getOpenFileName(self.widget, "Open PDF", "", "PDF Files (*.pdf)")
        if not filename:
            return

        pd = Progressing(self.view, 100, "Appending PDF...")

        def append():
            self.append_id = self.append_id + 1
            index = self.renderer.get_num_of_pages()
            num_of_pages_added = self.renderer.append_pdf(filename)

            for i in range(num_of_pages_added):
                page = self.view.create_page(index + i, self.view.get_ratio())
                page.update_original_info({"page": i, "append_id": self.append_id})
                self.view.layout_manager.update_layout(page)

                page = self.miniature_view.create_page(index + i, self.miniature_view.get_ratio())
                self.miniature_view.layout_manager.update_layout(page)

                pd.set_progress(i * 100 / num_of_pages_added)

            pd.set_progress(100)
            self.view.update_layout()
            self.miniature_view.update_layout()
            self.show_numbers()

        pd.start(append)

    def update_cursor(self, event):
        self.view: QGraphicsView
        pos = self.view.mapFromGlobal(QCursor.pos())

        item = self.view.itemAt(pos)
        if item is None:
            cursor = Qt.ArrowCursor
        elif event.modifiers() == Qt.ControlModifier:
            cursor = Qt.PointingHandCursor if isinstance(item, (SimplePage, SimplePage.Box)) else Qt.ArrowCursor
        elif isinstance(item, SimplePage):
            cursor = Qt.ArrowCursor
        elif isinstance(item, SimplePage.Box):
            cursor = Qt.ClosedHandCursor if QApplication.mouseButtons() == Qt.LeftButton else Qt.OpenHandCursor
        else:
            cursor = Qt.ArrowCursor
        # self.view.viewport().setCursor(cursor)
        self.view.viewport().setCursor(cursor)

    def mouse_pressed(self, event):

        self.update_cursor(event)

        if event.button() != Qt.LeftButton:
            return

        page = self.view.get_page_at_pos(event.pos())
        print("page", page)
        if page is None:
            self.state = self.STATE_RECT_SELECTION
            self.rb = SelectorRectItem()
            self.view.scene().addItem(self.rb)
            self.rb.view_mouse_press_event(self.view, event)
            self.rb.signals.creating.connect(self.rect_selection)
            self.clear_selected()

        elif event.modifiers() & Qt.ControlModifier:
            self.state = self.STATE_PAGE_SELECTION
            if page.is_selected():
                page.set_selected(False)
                if page in self.selected:
                    self.selected.remove(page)
            else:
                page.set_selected(True)
                self.selected.append(page)
        elif page.is_selected():
            self.state = self.STATE_PAGE_MOVING
            self.pickup_point = event.pos()
            self.leader_page = page
            for i, page in enumerate(self.selected):
                page.setZValue(100 + i)

    def mouse_moved(self, event):

        self.update_cursor(event)

        if self.state == self.STATE_RECT_SELECTION:
            self.rb.view_mouse_move_event(self.view, event)

        elif self.state == self.STATE_PAGE_MOVING:
            delta = event.pos() - self.pickup_point
            self.leader_page.moveBy(delta.x(), delta.y())

            i = 1
            for page in self.selected:
                if page is self.leader_page:
                    continue
                page.setPos(self.leader_page.pos() + QPointF(10 * i, 10 * i))
                i = i + 1

            self.pickup_point = event.pos()

            colliding_with = self.leader_page.collidingItems()
            colliding_with = [item for item in colliding_with if
                              isinstance(item, SimplePage) and item not in self.selected]

            if len(colliding_with) >= 1:
                page = colliding_with[-1]

                if self.leader_page.pos().x() + self.leader_page.get_scaled_width() / 2 > page.pos().x() + page.get_scaled_width() / 2:
                    self.collider.setPos(page.pos().x() + page.get_scaled_width(), page.pos().y())
                    # Right of page page.index
                    self.insert_at_page = (page.index, 1)
                else:
                    self.collider.setPos(page.pos().x() - 10, page.pos().y())
                    # Left of page page.index
                    self.insert_at_page = (page.index, 0)

                self.collider.setRect(0, 0, 10, page.get_scaled_height())
                self.collider.setVisible(True)
            else:
                self.insert_at_page = None
                self.collider.setVisible(False)

    def scene(self):
        return self.view.scene()

    def rearrange(self, ids):
        self.renderer.rearrange_pages(ids, False)

        for view in self.views:
            # pages = [view.get_page_item(i) for i in range(view.get_page_count())]
            # for i, idx in enumerate(ids):
            #     view.pages[i] = pages[idx]
            #     view.pages[i].index = i
            view.rearrange(ids)

    def key_pressed(self, event):
        self.update_cursor(event)

    def key_released(self, event):
        self.update_cursor(event)
        if event.key() == Qt.Key_Escape:
            self.clear_selected()

    def mouse_released(self, event):

        if self.state == self.STATE_PAGE_MOVING:
            self.collider.setVisible(False)
            for page in self.selected:
                page.setZValue(0)

            if self.insert_at_page is None:
                for view in self.views:
                    view.update_layout()
            else:
                # I'm actually changing
                # the order of the pages

                selected_index = [page.index for page in self.selected]
                ids = [i for i in range(self.view.get_page_count())]
                ids = move_numbers(ids, selected_index, self.insert_at_page)

                # Must be before rearrange otherwise
                # shine will restore the selection
                self.clear_selected()

                self.rearrange(ids)
                self.operation_done(False)
                self.notify_change(Action.PAGE_ORDER_CHANGED, {"indices": ids}, {"indices": ids})

        elif self.state == self.STATE_RECT_SELECTION:
            self.view.scene().removeItem(self.rb)
            self.rb = None

        self.state = None
        self.update_cursor(event)

    def rect_selection(self, rubberband):
        ci = self.rb.collidingItems()
        ci = [item for item in ci if isinstance(item, SimplePage)]
        for page in self.selected:
            page.set_selected(False)

        self.selected.clear()

        for page in ci:
            if page not in self.selected:
                page.set_selected(True)
                self.selected.append(page)
        print("rubberband", rubberband, ci)

    def operation_done(self, clear=True):
        for view in self.views:
            view.update_layout()
        self.leader_page = None
        self.insert_at_page = None
        self.pickup_point = None
        clear and self.clear_selected()

    def context_menu(self, event):
        if len(self.selected) == 0:
            return

        menu = QMenu()
        export_and_open = menu.addAction("Export" + " " + str(len(self.selected)) + " " + "pages and open")
        export = menu.addAction("Export" + " " + str(len(self.selected)) + " " + "pages")
        menu.addSeparator()
        delete = menu.addAction("Delete" + " " + str(len(self.selected)) + " " + "pages")
        duplicate = menu.addAction("Duplicate" + " " + str(len(self.selected)) + " " + "pages")
        rotate = menu.addMenu("Rotate " + " " + str(len(self.selected)) + " " + "pages")
        rotate.addAction("90° clockwise", lambda: self.action_rotate([p.index for p in self.selected], 90))
        rotate.addAction("90° counterclockwise", lambda: self.action_rotate([p.index for p in self.selected], -90))
        rotate.addAction("180°", lambda: self.action_rotate([p.index for p in self.selected], 180))
        menu.addSeparator()
        insert_blank = menu.addAction("Insert a blank pages after")
        # stack_blank = menu.addAction("Stack blank pages after")
        res = menu.exec_(event.globalPos())
        if res == delete:
            self.action_delete([p.index for p in self.selected])
        elif res == export:
            self.action_export(False)
        elif res == export_and_open:
            self.action_export(True)
        elif res == duplicate:
            self.action_duplicate([page.index for page in self.selected])
        elif res == insert_blank:
            self.action_insert_blank([page.index for page in self.selected])
        elif res == rotate:
            self.action_rotate([p.index for p in self.selected], 90)
        # elif res == stack_blank:
        #    self.action_stack_blank([page.index for page in self.selected])

    def undo(self, kind, info):
        if kind == Action.PAGE_ORDER_CHANGED:
            ask = self.config.should_continue("ask_undo_shuffle", "Proceed with undoing page reordering?")
            if ask:
                self.undo_order_change(kind, info)

        elif kind == Action.PAGES_ADDED:
            whole = list(range(len(self.view.pages)))
            for index, w, h in reversed(info["pages_added"]):
                whole.pop(index)

            self.rearrange(whole)

            for view in self.views:
                for p in view.pages.values():
                    p.invalidate()
                view.update_layout()

        elif kind == Action.PAGES_ROTATED:
            indices = info["indices"]
            angle = info["angle"]
            self.action_rotate(indices, -angle)
        elif kind == Action.PAGES_DUPLICATED:
            indices = info["indices"]
            helper, pages = [], []
            for i, index in enumerate(indices):
                if index not in helper:
                    helper.append(index)
                    pages.append(i)
            self.rearrange(pages)
            for p in self.view.pages.values():
                print(p.index)
            for view in self.views:
                view.update_layout()

    def redo(self, kind, info):
        if kind == Action.PAGE_ORDER_CHANGED:
            ask = self.config.should_continue("ask_undo_shuffle", "Proceed with redoing page reordering?")
            if ask:
                self.redo_order_change(kind, info)
        elif kind == Action.PAGES_ADDED:
            pages_added = info["pages_added"]
            for index, w, h in sorted(pages_added, reverse=True):
                self.renderer.insert_blank_page(index, w, h)

            for view in self.views:
                for index, w, h in sorted(pages_added, reverse=True):
                    view.insert_page(index)
                view.update_layout()

        elif kind == Action.PAGES_ROTATED:
            indices = info["indices"]
            angle = info["angle"]
            self.action_rotate(indices, angle)
        elif kind == Action.PAGES_DUPLICATED:
            indices = info["indices"]
            print("indiceees", indices)
            self.rearrange(indices)
            for view in self.views:
                view.update_layout()

    def undo_order_change(self, kind, info):
        order = info["indices"]

        # !!! self.view.pages are the index of the pages !!!
        zipped = list(zip(order, self.view.pages))
        zipped.sort(key=lambda x: x[0])
        _, new_order = zip(*zipped)
        self.rearrange(new_order)
        for view in self.views:
            view.update_layout()

    def redo_order_change(self, kind, info):
        order = info["indices"]
        self.rearrange(order)
        for view in self.views:
            view.update_layout()

    def finish(self):
        self.pickup_point = None
        self.leader_page = None
        self.view.scene().removeItem(self.collider)
        self.collider = None
        self.insert_at_page = None
        self.clear_selected()

        for page in self.selected:
            page.setZValue(0)

        if self.view.get_ratio() == 0.25:
            self.view.set_ratio(self.orig_ratio, True)

        self.widget.remove_app_widget()
        self.helper.deleteLater()

    def action_duplicate(self, indices):

        list_of_pages = list(range(len(self.view.pages)))
        for index in indices:
            where = list_of_pages.index(index)
            list_of_pages.insert(where, index)

        self.renderer.rearrange_pages(list_of_pages, False)
        for view in self.views:
            view.rearrange(list_of_pages)
            view.update_layout()

        self.notify_change(Action.PAGES_DUPLICATED, {"indices": list_of_pages}, {"indices": list_of_pages})
        self.show_numbers()

    def action_delete(self, deleting):
        if self.config.should_continue("ask_delete", "This operation is not undoable and will clear the undo stack.\nProceed?"):

            # Delete the selected pages
            remaining = [i for i in range(len(self.view.pages)) if i not in deleting]
            self.renderer.rearrange_pages(remaining, False)
            for view in self.views:
                view.rearrange(remaining)

        self.operation_done()
        self.notify_not_undoable()

    def action_stack_blank(self, indices):
        pages_added = []
        for i, index in enumerate(sorted(indices, reverse=False)):
            w, h = self.renderer.get_page_size(index)
            self.renderer.insert_blank_page(indices[-1] + i + 1, w, h)
            pages_added.append(indices[-1] + i + 1)
            for view in self.views:
                view.insert_page(indices[-1] + i + 1)

        self.operation_done()
        self.notify_change(Action.PAGES_ADDED, {"pages_added": pages_added}, {"pages_added": pages_added})

    def action_insert_blank(self, indices):
        pages_added = []
        for index in sorted(indices, reverse=True):
            w, h = self.renderer.get_page_size(index)
            self.renderer.insert_blank_page(index + 1, w, h)
            pages_added.append((index + 1, w, h))

        for view in self.views:
            for index in sorted(indices, reverse=True):
                view.insert_page(index + 1)

        self.operation_done()
        self.notify_change(Action.PAGES_ADDED, {"pages_added": pages_added}, {"pages_added": pages_added})
        self.show_numbers()

    def action_export(self, open_pdf):
        filename, _ = QFileDialog.getSaveFileName(self.view, "Save PDF Document", self.renderer.get_filename(),
                                                  "PDF Files (*.pdf)")
        if filename:
            if self.renderer.export_pages([page.index for page in self.selected], filename):
                if open_pdf:
                    self.emit_finished()
                    self.renderer.open_pdf(filename)
                else:
                    QMessageBox.information(self.view, "Export", "Exported" + " " + str(
                        len(self.selected)) + " " + "pages to" + " " + filename)
            else:
                QMessageBox.critical(self.view, "Export", "Error exporting pages")

    def action_rotate(self, indices, angle):
        for index in indices:
            self.renderer.rotate_page(index, angle)
            for view in self.views:
                page = view.pages[index]
                page.invalidate()
        for view in self.views:
            view.update_layout()

        info = {"indices": [p.index for p in self.selected], "angle": angle}
        self.notify_change(Action.PAGES_ROTATED, info, info)

    def clear_selected(self):
        for page in self.selected:
            page.set_selected(False)
        self.selected.clear()
