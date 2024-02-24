from PyQt5.QtCore import QObject, pyqtSignal


class Tool(QObject):
    finished = pyqtSignal()

    def __init__(self, view, renderer):
        super(Tool, self).__init__()
        self.view = view
        self.renderer = renderer

    def mouse_pressed(self, event):
        pass

    def mouse_released(self, event):
        pass

    def mouse_moved(self, event):
        pass

    def context_menu(self, event):
        pass

    def done(self):
        pass
