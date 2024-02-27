class Atom:
    def __init__(self, item, kind, old=None, new=None):
        self.kind = kind
        self.item = item
        self.old = old
        self.new = new


class Action(list):
    ACTION_CREATE = 0
    ACTION_REMOVE = 1
    ACTION_CHANGED = 2
    ACTION_FULL_STATE = 3

    def __init__(self, item, kind, old=None, new=None):
        super().__init__()
        self.push(item, kind, old, new)

    def push(self, item, kind, old=None, new=None):
        super().append(Atom(item, kind, old, new))


class CreateAction(Action):
    def __init__(self, item):
        super().__init__(item, Action.ACTION_CREATE, item.parentItem())

    def item(self):
        return self[0].item
