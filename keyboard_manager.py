from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut


class KeyboardManager(object):
    PRESS = 0
    RELEASE = 1
    def __init__(self, widget):
        self.press_actions = {}
        self.release_actions = {}
        self.combination_actions = {}
        self.widget = widget

    def register_action(self, key, action1=None, action2=None):
        if action1 is not None:
            self.press_actions[key] = action1
        if action2 is not None:
            self.release_actions[key] = action2

    def register_combination_action(self, keys, action):
        self.combination_actions[keys] = action
        x_mode = QShortcut(QKeySequence(keys), self.widget)
        x_mode.activated.connect(action)

    def key_pressed(self, event):
        if event.key() in self.press_actions:
            self.press_actions[event.key()]()
            return True
        return False

    def key_released(self, event):
        if event.key() in self.release_actions:
            self.release_actions[event.key()]()
            return True
        return False
