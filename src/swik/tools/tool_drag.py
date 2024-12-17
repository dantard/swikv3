from PyQt5.QtWidgets import QGraphicsView

from swik.tools.tool import Tool


class ToolDrag(Tool):

    def init(self):
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)

    def finish(self):
        self.view.setDragMode(QGraphicsView.NoDrag)