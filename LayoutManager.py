import math

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsView

from simplepage import SimplePage


class LayoutManager:
    # ## Modes
    MODE_VERTICAL = 0
    MODE_VERTICAL_MULTIPAGE = 1
    MODE_HORIZONTAL = 2
    MODE_SINGLE_PAGE = 3

    modes = {MODE_VERTICAL: 'Vertical', MODE_VERTICAL_MULTIPAGE: 'Multi page',
             MODE_HORIZONTAL: 'Horizontal', MODE_SINGLE_PAGE: 'Single Page'}

    ratio_max = 5
    ratio_min = 0.25

    def __init__(self, renderer):
        self.renderer = renderer
        self.scene_width = 0
        self.scene_height = 0

    def clear(self):
        self.scene_width = 0
        self.scene_height = 0

    def update_layout(self, view, page):

        max_width, max_height = self.renderer.get_max_pages_size()

        def single_row(page):
            if page.index == 0:
                x_pos = 20
            else:
                x_pos = view.pages[page.index - 1].pos().x() + view.pages[page.index - 1].get_scaled_width() + page.get_sep()

            self.scene_width = max(self.scene_width, x_pos + page.get_scaled_width() + page.get_sep())
            page.setPos(x_pos, max_height * page.get_scaling_ratio() / 2 - page.get_scaled_height() / 2)
            view.scene().setSceneRect(0, 0, self.scene_width, max_height * page.get_scaling_ratio())

        def single_column_fit_width(page):
            y_pos = 20 if page.index == 0 else view.pages[page.index - 1].pos().y() + view.pages[page.index - 1].get_scaled_height() + page.get_sep()
            self.scene_height = max(self.scene_height, y_pos + page.get_scaled_height() + page.get_sep())
            view.scene().setSceneRect(0, 0, page.get_scaled_width(), self.scene_height)
            page.setPos(0, y_pos)

        def single_column(page):
            y_pos = 20 if page.index == 0 else view.pages[page.index - 1].pos().y() + view.pages[page.index - 1].get_scaled_height() + page.get_sep()
            self.scene_height = max(self.scene_height, y_pos + page.get_scaled_height() + page.get_sep())
            view.scene().setSceneRect(0, 0, max_width * page.get_scaling_ratio(), self.scene_height)
            page.setPos(max_width * page.get_scaling_ratio() / 2 - page.get_scaled_width() / 2, y_pos)

        # print("page processedas ****** ", page.index, view.mode)

        if view.mode == self.MODE_SINGLE_PAGE:
            if page.index == view.page:
                page.setPos(0, 0)
                view.scene().setSceneRect(0, 0, page.get_scaled_width(), page.get_scaled_height())
                page.setVisible(True)
            else:
                page.setVisible(False)

        elif view.is_fitting_width():
            single_column_fit_width(page)

        elif view.mode == self.MODE_VERTICAL_MULTIPAGE:
            page.setVisible(True)
            s_max_width, s_max_height = max_width * page.get_scaling_ratio(), max_height * page.get_scaling_ratio()
            max_num_horiz_pages = max(view.viewport().width() // (s_max_width + 2 * page.get_sep()), 1)
            num_cols = min(self.renderer.get_num_of_pages(), max_num_horiz_pages)
            # num_rows = math.ceil(len(view.pages) / num_cols)

            if num_cols == 1:
                single_column(page)
            else:
                row = page.index // max_num_horiz_pages
                col = page.index % max_num_horiz_pages
                dx = (s_max_width - page.get_scaled_width()) / 2
                x = page.get_sep() + col * (s_max_width + page.get_sep()) + dx
                # print("page", page.index, "scaled height", page.get_scaled_height(), page.get_scaling_ratio(), page.get_orig_height())

                dy = (s_max_height - page.get_scaled_height()) / 2
                y = row * (s_max_height + page.get_sep()) + dy
                page.setPos(x, page.get_sep() + y)
                self.scene_height = max(self.scene_height, y + page.get_scaled_height() + page.get_sep())
                self.scene_width = max(self.scene_width, x + page.get_scaled_width() + page.get_sep())
                view.scene().setSceneRect(0, 0, self.scene_width, self.scene_height + page.get_sep())

        elif view.mode == self.MODE_VERTICAL:
            page.setVisible(True)
            single_column(page)

        elif view.mode == self.MODE_HORIZONTAL:
            page.setVisible(True)
            single_row(page)
