from PyQt5.QtCore import QObject, pyqtSignal
from easyconfig import EasyConfig


class BasicTool(QObject):
    finished = pyqtSignal()

    def __init__(self, view, renderer, config):
        super(BasicTool, self).__init__()
        self.view = view
        self.renderer = renderer
        self.config: EasyConfig = config

    def configure(self):
        pass

    def init(self):
        pass

    def finish(self):
        pass

    def keyboard(self, combination):
        pass

    def context_menu(self, event):
        pass


class Tool(BasicTool):

    def mouse_pressed(self, event):
        pass

    def mouse_released(self, event):
        pass

    def mouse_moved(self, event):
        pass

    def mouse_double_clicked(self, event):
        pass


