from PyQt5.QtCore import QMimeData, QUrl, Qt, QPointF
from PyQt5.QtGui import QDrag

from bunch import Bunch, AnchoredBunch, NumerateBunch
from swiktext import SwikTextNumerate
from tools.tool import BasicTool, Tool


class ToolNumerate(BasicTool):
    def __init__(self, name, icon, parent, **kwargs):
        super(ToolNumerate, self).__init__(name, icon, parent)
        self.font_manager = kwargs.get('font_manager')
        self.numbers = []

    def init(self):
        bunch = NumerateBunch(self.view.scene())
        for i in range(0, self.view.get_page_count()):
            number = SwikTextNumerate(str(i + 1), self.view.pages[i], self.font_manager, '@base14/helv', 12)
            bunch.add(number)
        self.finished.emit()
