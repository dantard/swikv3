from PyQt5 import QtCore

from annotations.annotation import Annotation


class SquareAnnotation(Annotation):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)


