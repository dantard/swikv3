from PyQt5.QtCore import QMimeData, QUrl, Qt
from PyQt5.QtGui import QDrag

from tools.tool import BasicTool, Tool


class ToolDrag(Tool):
    def __init__(self, name, icon, parent):
        super(ToolDrag, self).__init__(name, icon, parent)

    def mouse_pressed(self, event):
        print("jajajajsssssssssssssss")
        event.accept()
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(self.renderer.get_filename())])
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)
        self.finished.emit()


