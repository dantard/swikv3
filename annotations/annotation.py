from resizeable import ResizableRectItem


class Annotation(ResizableRectItem):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.content = str()

    def set_content(self, text):
        self.content = text

    def get_content(self):
        return self.text
