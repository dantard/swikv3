from PyQt5.QtWidgets import QWidget


class Copyable:

    def duplicate(self):
        pass


class Undoable:

    def notify_creation(self, item=None, scene=None):
        scene = self.scene() if scene is None else scene
        self.scene().tracker().item_added(item if item is not None else self)

    def notify_deletion(self, item=None, scene=None):
        scene = self.scene() if scene is None else scene
        scene.tracker().item_removed(item if item is not None else self)

    def notify_change(self, kind, old, new, scene=None):
        if old != new:
            scene = self.scene() if scene is None else scene
            # scene.tracker().item_changed(Action(self, kind, old, new))
            scene.notify_change(self, kind, old, new)

    def notify_any_change(self, kind, old, new, scene=None):
        if old != new:
            scene = self.scene() if scene is None else scene
            # scene.tracker().item_changed(Action(self, kind, old, new))
            scene.notify_any_change(kind, self, old, new)

    def notify_position_change(self, old, new, scene=None):
        scene = self.scene() if scene is None else scene
        scene.notify_position_change(self, old, new)

    def undo(self, kind, info):
        pass

    def redo(self, kind, info):
        self.undo(kind, info)



class Shell(QWidget):
    def get_renderer(self):
        pass

    def get_view(self):
        pass

    def get_manager(self):
        pass

    def get_config(self):
        pass

    def get_font_manager(self):
        pass

    def get_other_views(self):
        pass

    def set_app_widget(self, widget, width=500, title=""):
        pass

    def remove_app_widget(self):
        pass
