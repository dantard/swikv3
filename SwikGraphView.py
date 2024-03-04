from GraphView import GraphView
from LayoutManager import LayoutManager
from annotations.highlight_annotation import HighlightAnnotation
from annotations.redactannotation import RedactAnnotation
from annotations.squareannotation import SquareAnnotation
from page import Page
from simplepage import SimplePage
from swiktext import SwikText
from widgets.pdf_widget import PdfWidget


class SwikGraphView(GraphView):

    def __init__(self, manager, renderer, scene, page=SimplePage, mode=LayoutManager.MODE_VERTICAL_MULTIPAGE):
        super(SwikGraphView, self).__init__(manager, renderer, scene, page, mode)
        self.renderer.sync_requested.connect(self.sync_requested)

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

        swik_text = [item for item in items if type(item) == SwikText]
        for text in swik_text:
            page: Page = text.parentItem()
            self.renderer.add_text(page.get_index(), text)

        swik_text = [item for item in items if type(item) == HighlightAnnotation]
        for text in swik_text:
            page: Page = text.parentItem()
            self.renderer.add_highlight_annot(page.index, text)

        widgets = [item for item in items if isinstance(item,PdfWidget)]
        for widget in widgets:
            page: Page = widget.parentItem()
            self.renderer.add_widget(page.get_index(), widget)



        for index in pages_to_refresh:
            self.pages[index].invalidate()

    def page_processed(self, page):
        super().page_processed(page)
        self.renderer.get_annotations(page)
        self.renderer.get_widgets(page)