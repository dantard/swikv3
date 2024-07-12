from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtWidgets import QApplication

from swik.miniature_page import MiniaturePage


class LayoutManager:
    # ## Modes
    MODE_VERTICAL = 0
    MODE_VERTICAL_MULTIPAGE = 1
    MODE_HORIZONTAL = 2
    MODE_SINGLE_PAGE = 3
    MODE_FIT_WIDTH = 4

    modes = {MODE_VERTICAL: 'Vertical', MODE_VERTICAL_MULTIPAGE: 'Multi page',
             MODE_HORIZONTAL: 'Horizontal', MODE_SINGLE_PAGE: 'Single Page', MODE_FIT_WIDTH: 'Fit Width'}

    Vertical = [MODE_VERTICAL, MODE_VERTICAL_MULTIPAGE, MODE_SINGLE_PAGE, MODE_FIT_WIDTH]

    ratio_max = 5
    ratio_min = 0.25

    def __init__(self, view, renderer, mode=MODE_VERTICAL, align=Qt.AlignVCenter | Qt.AlignHCenter, page_sep=27):
        self.view = view
        self.renderer = renderer
        self.mode = mode
        self.page_sep = page_sep
        self.scene_width, self.scene_height = 0, 0
        self.max_width, self.max_height = 0, 0
        self.view.scene().setSceneRect(QRectF())
        self.align = align

        self.reset()

    def get_mode(self):
        return self.mode

    def is_vertical(self):
        return self.mode in self.Vertical

    def set_mode(self, mode, update=True):
        print("UPDAAAAAAAAAAAAAAAAAAAAAATE MODEEEEEEEEE")
        self.mode = mode
        if update:
            self.reset()
            self.fully_update_layout()

    def fully_update_layout(self):
        self.reset()
        for i in range(self.renderer.get_num_of_pages()):
            if (p := self.view.pages.get(i)) is not None:
                self.update_layout(p)
        self.view.update()
        QApplication.processEvents()

    def init(self):
        self.scene_width, self.scene_height = 0, 0
        self.max_width, self.max_height = self.renderer.get_max_pages_size()

    def reset(self):
        if self.mode == self.MODE_SINGLE_PAGE:
            return
        self.scene_width, self.scene_height = 0, 0
        self.max_width, self.max_height = self.renderer.get_max_pages_size()
        rect = self.compute_scene_rect()
        self.view.scene().setSceneRect(rect)
        self.view.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        self.view.setAlignment(self.align)

    def compute_scene_rect(self):
        if self.mode == self.MODE_SINGLE_PAGE:
            return QRectF(0, 0, 0, 0)
        else:
            max_width, max_height = 0, 20
            for index in range(self.renderer.get_num_of_pages()):
                w, h = self.renderer.get_page_size(index)
                ratio = self.view.get_ratio() if self.mode != self.MODE_FIT_WIDTH else 1 / (w / (self.view.viewport().width() - 20))
                w = w * ratio
                h = h * ratio
                max_width = max(max_width, w)
                max_height = max_height + h + self.page_sep
            # ri.setRect(0, 0, max_width, max_height)
            # self.view.scene().addItem(ri)
            return QRectF(0, 0, max_width, max_height)

    def single_row(self, page):
        x_pos = 20 if page.index == 0 else self.view.pages[page.index - 1].pos().x() + self.view.pages[page.index - 1].get_scaled_width() + self.page_sep
        self.scene_width = max(self.scene_width, x_pos + page.get_scaled_width() + self.page_sep)
        self.view.scene().setSceneRect(0, 0, self.scene_width, self.max_height * page.get_scaling_ratio())
        page.setPos(x_pos, self.max_height * page.get_scaling_ratio() / 2 - page.get_scaled_height() / 2)

    def single_column_fit_width(self, page):
        ratio = page.get_orig_width() / (self.view.viewport().width() - 20)
        page.update_image(1 / ratio)
        y_pos = 20 if page.index == 0 else self.view.pages[page.index - 1].pos().y() + self.view.pages[page.index - 1].get_scaled_height() + self.page_sep
        self.scene_height = max(self.scene_height, y_pos + page.get_scaled_height() + self.page_sep)
        # self.view.scene().setSceneRect(0, 0, page.get_scaled_width(), self.scene_height)
        page.setPos(0, y_pos)
        page.setVisible(True)

    def single_column(self, page):
        y_pos = 20 if page.index == 0 else self.view.pages[page.index - 1].pos().y() + self.view.pages[page.index - 1].get_scaled_height() + self.page_sep
        self.scene_height = max(self.scene_height, y_pos + page.get_scaled_height() + self.page_sep)
        # self.view.scene().setSceneRect(0, 0, self.max_width * page.get_scaling_ratio(), self.scene_height)

        sw, sh = self.view.scene().sceneRect().width(), self.view.scene().sceneRect().height()
        pw = page.get_scaled_width()

        page.setPos(sw / 2 - pw / 2, y_pos)
        page.setVisible(True)

    def vertical_multipage(self, page):
        page.setVisible(True)
        s_max_width, s_max_height = self.max_width * page.get_scaling_ratio(), self.max_height * page.get_scaling_ratio()
        max_num_horiz_pages = max(self.view.viewport().width() // (s_max_width + 2 * self.page_sep), 1)
        num_cols = min(self.renderer.get_num_of_pages(), max_num_horiz_pages)

        if num_cols == 1:
            self.single_column(page)
        else:
            row = page.index // max_num_horiz_pages
            col = page.index % max_num_horiz_pages
            dx = (s_max_width - page.get_scaled_width()) / 2
            x = self.page_sep + col * (s_max_width + self.page_sep) + dx
            dy = (s_max_height - page.get_scaled_height()) / 2
            y = row * (s_max_height + self.page_sep) + dy
            page.setPos(x, self.page_sep + y)
            self.scene_height = max(self.scene_height, y + page.get_scaled_height() + self.page_sep)
            self.scene_width = max(self.scene_width, x + page.get_scaled_width() + self.page_sep)
            self.view.scene().setSceneRect(0, 0, self.scene_width, self.scene_height + self.page_sep)

    def move_to_page(self, page):
        if self.mode == self.MODE_SINGLE_PAGE:
            for p in self.view.pages.values():
                p.setVisible(False)
            self.update_layout(page)

    def update_layout(self, page):

        if self.mode == self.MODE_SINGLE_PAGE:
            if page.index == self.view.get_page():
                self.reset()
                w, h = self.renderer.get_page_size(page.index)
                ratio = self.view.get_ratio()
                w = w * ratio
                h = h * ratio
                self.view.scene().setSceneRect(QRectF(0, 0, w, h + 40))
                page.setPos(0, 20)
                page.setVisible(True)
                self.view.setAlignment(Qt.AlignBottom | Qt.AlignRight)
                self.view.setAlignment(self.align)
            else:
                page.setVisible(False)

        elif self.mode == self.MODE_FIT_WIDTH:
            self.single_column_fit_width(page)
        elif self.mode == self.MODE_VERTICAL_MULTIPAGE:
            self.vertical_multipage(page)
        elif self.mode == self.MODE_VERTICAL:
            self.single_column(page)
        elif self.mode == self.MODE_HORIZONTAL:
            self.single_row(page)

        if type(page) == MiniaturePage:
            page.number.setPlainText(str(page.index + 1))
