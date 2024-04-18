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

    def register_action(self, key, press_action=None, release_action=None):
        if press_action is not None:
            self.press_actions[key] = press_action
        if release_action is not None:
            self.release_actions[key] = release_action

    def register_combination_action(self, keys, action):
        self.combination_actions[keys] = action
        x_mode = QShortcut(QKeySequence(keys), self.widget)
        x_mode.activated.connect(action)

    def key_pressed(self, event):
        print("key_pressed", event)
        if event.key() in self.press_actions:
            self.press_actions[event.key()]()
            return True
        elif event.key() in self.release_actions:
            return True
        return False

    def key_released(self, event):
        if event.key() in self.release_actions:
            print("ibne")
            self.release_actions[event.key()]()
            return True
        elif event.key() in self.press_actions:
            print("tqtq")
            return True

        return False
