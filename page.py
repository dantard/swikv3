from simplepage import SimplePage


class Page(SimplePage):
    def __init__(self, index, view, manager, renderer, ratio):
        super().__init__(index, view, manager, renderer, ratio)
        self.words = None

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)

    def set_words(self, words, join=True):
        self.words = words
        for word in self.words:
            word.join(self)

    def has_words(self):
        return self.words is not None

    def get_words(self):
        return self.words
