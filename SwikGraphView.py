from PyQt5.QtCore import pyqtSignal

from GraphView import GraphView
from LayoutManager import LayoutManager
from annotations.highlight_annotation import HighlightAnnotation
from annotations.redactannotation import RedactAnnotation
from annotations.squareannotation import SquareAnnotation
from page import Page
from simplepage import SimplePage
from swiktext import SwikText, SwikTextReplace, SwikTextNumerate
from tools.tool_insert_image import InsertImageRectItem
from widgets.pdf_widget import PdfWidget


class SwikGraphView(GraphView):
    drop_event = pyqtSignal(list)

    def __init__(self, manager, renderer, scene, page=SimplePage, mode=LayoutManager.MODE_VERTICAL_MULTIPAGE):
        super(SwikGraphView, self).__init__(manager, renderer, scene, page, mode)
        self.renderer.sync_requested.connect(self.sync_requested)
        self.setAcceptDrops(True)

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

    def sync_requested(self):
        items = self.scene().items()
        pages_to_refresh = set()

        redact_annot = [item for item in items if type(item) == RedactAnnotation]
        for annot in redact_annot:  # type: RedactAnnotation
            page: Page = annot.parentItem()
            self.renderer.add_redact_annot(page.index, annot.get_rect_on_parent(), annot.brush().color())
            pages_to_refresh.add(page.index)
            self.scene().removeItem(annot)

        square_annot = [item for item in items if type(item) == SquareAnnotation]
        for annot in square_annot:  # type: RedactAnnotation
            page: Page = annot.parentItem()
            self.renderer.add_annot(page.get_index(), annot)

        highlight_annot = [item for item in items if type(item) == HighlightAnnotation]
        for annot in highlight_annot:
            page: Page = annot.parentItem()
            self.renderer.add_highlight_annot(page.index, annot)
            pages_to_refresh.add(page.get_index())

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

        widgets = [item for item in items if isinstance(item, PdfWidget)]
        for widget in widgets:
            page: Page = widget.parentItem()
            self.renderer.add_widget(page.get_index(), widget)
            pages_to_refresh.add(page.get_index())

        images = [item for item in items if isinstance(item, InsertImageRectItem)]
        for image in images:
            page: Page = image.parentItem()
            self.renderer.insert_image(page.get_index(), image.get_image_rect_on_parent(), image.get_image())
            pages_to_refresh.add(page.get_index())
            self.scene().removeItem(image)

        for index in pages_to_refresh:
            self.pages[index].invalidate()

    def page_processed(self, page):
        super().page_processed(page)
        self.renderer.get_annotations(page)
        self.renderer.get_widgets(page)

    def toggle_page_info(self):
        for page in self.pages.values():
            page.toggle_info()
