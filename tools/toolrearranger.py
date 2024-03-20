from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtWidgets import QGraphicsRectItem, QMenu, QFileDialog, QMessageBox

from action import Action
from interfaces import Undoable
from selector import SelectorRectItem
from simplepage import SimplePage
from tools.tool import Tool


def move_numbers(vector, numbers_to_move, position):

    # Remove the selected numbers from the vector
    for number in numbers_to_move:
        vector.remove(number)

    position, side = position

    # Find the index where to insert the numbers
    insert_index = vector.index(position)
    insert_index = insert_index + 1  if side == 1 else insert_index

    # Insert the numbers at the specified position
    for number in reversed(numbers_to_move):
        vector.insert(insert_index, number)

    return vector


class ToolRearrange(Tool, Undoable):
    STATE_RECT_SELECTION = 0
    STATE_PAGE_SELECTION = 1
    STATE_PAGE_MOVING = 2

    def __init__(self, view, other_views, renderer, config):
        super().__init__(view, renderer, config)
        self.selected = []
        self.pickup_point = None
        self.leader_page = None
        self.collider = None
        self.insert_at_page = None
        self.state = None
        self.orig_ratio = None

    def init(self):
        self.collider = QGraphicsRectItem()
        self.collider.setBrush(Qt.red)
        self.collider.setVisible(False)
        self.view.scene().addItem(self.collider)
        self.orig_ratio = self.view.get_ratio()
        self.view.set_ratio(0.25, True)

    def mouse_pressed(self, event):
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

                if self.leader_page.pos().x() > page.pos().x() + page.get_scaled_width() / 2:
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

    def mouse_released(self, event):
        if self.state == self.STATE_PAGE_MOVING:
            self.collider.setVisible(False)
            for page in self.selected:
                page.setZValue(0)

            if self.insert_at_page is None:
                for view in self.views:
                    view.fully_update_layout()
            else:
                # I'm actually change order of pages
                for page in self.selected:
                    page.set_selected(False)

                selected_index = [page.index for page in self.selected]
                ids = [i for i in range(self.view.get_page_count())]
                move_numbers(ids, selected_index, self.insert_at_page)

                for view in self.views:
                    pages = [view.get_page_item(i) for i in range(view.get_page_count())]
                    for i, idx in enumerate(ids):
                        view.pages[i] = pages[idx]
                        view.pages[i].index = i

                self.renderer.rearrange_pages(ids, False)

                self.notify_change(Action.PAGE_ORDER_CHANGED, list(range(len(self.view.pages))), ids, self.view.scene())
                self.operation_done()
        elif self.state == self.STATE_RECT_SELECTION:
            self.view.scene().removeItem(self.rb)
            self.rb = None

        self.state = None

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

    def operation_done(self):
        for view in self.views:
            view.fully_update_layout()
        self.leader_page = None
        self.insert_at_page = None
        self.pickup_point = None
        self.selected.clear()
        for p in self.selected:
            p.set_selected(False)

    def context_menu(self, event):
        if len(self.selected) == 0:
            return

        menu = QMenu()
        export_and_open = menu.addAction("Export" + " " + str(len(self.selected)) + " " + "pages and open")
        export = menu.addAction("Export" + " " + str(len(self.selected)) + " " + "pages")
        menu.addSeparator()
        delete = menu.addAction("Delete" + " " + str(len(self.selected)) + " " + "pages")
        duplicate = menu.addAction("Duplicate" + " " + str(len(self.selected)) + " " + "pages")
        insert_blank = menu.addAction("Insert a blank pages after")
        res = menu.exec_(event.globalPos())
        if res == delete:
            # Delete the selected pages
            deleting = [p.index for p in self.selected]
            remaining = [i for i in range(len(self.view.pages)) if i not in deleting]
            self.renderer.rearrange_pages(remaining, False)
            for view in self.views:
                view.rearrange(remaining)

            self.operation_done()
        elif res == export:
            filename, _ = QFileDialog.getSaveFileName(self.view, "Save PDF Document", self.renderer.get_filename(),
                                                      "PDF Files (*.pdf)")
            if filename:
                if self.renderer.export([page.index for page in self.selected], filename):
                    QMessageBox.information(self.view, "Export", "Exported" + " " + str(
                        len(self.selected)) + " " + "pages to" + " " + filename)
                else:
                    QMessageBox.critical(self.view, "Export", "Error exporting pages")
        elif res == export_and_open:
            filename, _ = QFileDialog.getSaveFileName(self.view, "Save PDF Document", self.renderer.get_filename(),
                                                      "PDF Files (*.pdf)")
            if filename:
                if self.renderer.export_pages([page.index for page in self.selected], filename):
                    self.finished.emit()
                    self.renderer.open_pdf(filename)
                else:
                    QMessageBox.critical(self.view, "Export", "Error exporting pages")
        elif res == duplicate:
            indices = [page.index for page in self.selected]
            list_of_pages = list(range(len(self.view.pages)))
            for index in indices:
                where = list_of_pages.index(index)
                list_of_pages.insert(where, index)

            self.renderer.rearrange_pages(list_of_pages, False)
            for view in self.views:
                view.rearrange(list_of_pages)
                view.fully_update_layout()
        elif res == insert_blank:
            pass

    def undo(self, kind, info):
        print(kind, info)

    def finish(self):
        self.pickup_point = None
        self.leader_page = None
        self.view.scene().removeItem(self.collider)
        self.collider = None
        self.insert_at_page = None
        self.selected.clear()
        for page in self.selected:
            page.setZValue(0)

        print("finishhhhh")
        if self.view.get_ratio()==0.25:
            self.view.set_ratio(self.orig_ratio, True)
