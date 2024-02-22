from PyQt5.QtCore import QObject

from rubberband import RubberBand


class Manager(QObject):

    def __init__(self):
        super(Manager, self).__init__()
        print("Manager created")
        self.rb:RubberBand = None

    def mouse_pressed(self, source, event):
        print("Manager mouse pressed", event.pos())
        self.rb = RubberBand(source.get_view(), source)
        self.rb.mouse_press(event.scenePos())

    def mouse_released(self, source, event):
        print("Manager mouse released")
        self.rb.mouse_release(event.scenePos())

    def mouse_moved(self, source, event):
        print("Manager mouse moved")
        self.rb.mouse_move(event.scenePos())

    def generic_rubberband(self, source, event):
        print("Manager generic rubberband")