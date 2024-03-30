from PyQt5.QtCore import QObject, pyqtSignal


class BasicTool(QObject):
    finished = pyqtSignal()

    def __init__(self, view, renderer, config):
        super(BasicTool, self).__init__()
        self.view = view
        self.renderer = renderer
        self.config = config

    @staticmethod
    def configure(self):
        pass

    def preference_changed(self):
        pass

    def init(self):
        pass

    def finish(self):
        pass

    def keyboard(self, combination):
        pass

    def context_menu(self, event):
        pass

    def usable(self):
        return True


class Tool(BasicTool):

    def mouse_pressed(self, event):
        pass

    def mouse_released(self, event):
        pass

    def mouse_moved(self, event):
        pass

    def mouse_double_clicked(self, event):
        pass
