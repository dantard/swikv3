from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QApplication

from tools.tool import Tool
from widgets.pdf_widget import PdfWidget


class ToolForm(Tool):

    def __init__(self, view, renderer, config, **kwargs):
        super().__init__(view, renderer, config)
        self.rubberband = None
        self.widget = kwargs.get('widget', None)
        self.helper = None
        self.preview_btn = None
        self.clear_btn = None
        self.flatten_btn = None
        self.tree = None

    def init(self):
        v_layout = QVBoxLayout()
        self.helper = QWidget()

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setCheckable(True)
        self.preview_btn.clicked.connect(self.preview)
        self.flatten_btn = QPushButton("Flatten")
        self.flatten_btn.clicked.connect(self.flatten)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_fields)

        v_layout.setAlignment(Qt.AlignTop)
        v_layout.addWidget(self.preview_btn)
        v_layout.addWidget(self.clear_btn)
        v_layout.addWidget(self.flatten_btn)
        self.helper.setLayout(v_layout)
        self.widget.set_app_widget(self.helper, 100, "Form")

    def flatten(self):
        self.widget.flatten()

    def clear_fields(self):
        widgets = [item for item in self.view.items() if isinstance(item, PdfWidget)]
        for widget in widgets:
            widget.clear()

    def preview(self):

        self.flatten_btn.setEnabled(not self.preview_btn.isChecked())
        self.clear_btn.setEnabled(not self.preview_btn.isChecked())
        QApplication.processEvents()

        widgets = [item for item in self.view.items() if isinstance(item, PdfWidget)]
        pages_to_invalidate = set()

        if self.preview_btn.isChecked():
            for widget in widgets:
                self.renderer.add_widget(widget.parentItem().index, widget)
                pages_to_invalidate.add(widget.parentItem().index)
                widget.setVisible(False)

            for index in pages_to_invalidate:
                self.view.pages[index].invalidate()
                self.widget.miniature_view.pages[index].invalidate()

        else:
            for widget in widgets:
                widget.setVisible(True)

    def usable(self):
        return True

    def finish(self):
        widgets = [item for item in self.view.items() if isinstance(item, PdfWidget)]
        for widget in widgets:
            widget.setVisible(True)
        self.view.setCursor(Qt.ArrowCursor)
        self.widget.remove_app_widget()
