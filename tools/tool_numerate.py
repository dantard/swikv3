from PyQt5.QtCore import QMimeData, QUrl, Qt
from PyQt5.QtGui import QDrag

from tools.tool import BasicTool, Tool


class ToolNumerate(Tool):
    def __init__(self, name, icon, parent):
        super(ToolNumerate, self).__init__(name, icon, parent)

    def init(self):
        pass


