from PyQt5.QtCore import QObject, pyqtSignal
from easyconfig import EasyConfig


class Tool(QObject):
    finished = pyqtSignal()

    def __init__(self, view, renderer, config):
        super(Tool, self).__init__()
        self.view = view
        self.renderer = renderer
        self.config: EasyConfig = config

    def configure(self):
        pass

    def mouse_pressed(self, event):
        pass

    def mouse_released(self, event):
        pass

    def mouse_moved(self, event):
        pass

    def context_menu(self, event):
        pass

    def init(self):
        pass

    def finish(self):
        pass
