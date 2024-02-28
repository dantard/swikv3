from GraphView import GraphView
from LayoutManager import LayoutManager
from simplepage import SimplePage


class SwikGraphView(GraphView):

    def __init__(self, manager, renderer, scene, page=SimplePage, mode=LayoutManager.MODE_VERTICAL_MULTIPAGE):
        super(SwikGraphView, self).__init__(manager, renderer, scene, page, mode)
        self.renderer.sync_requested.connect(self.sync_requested)


    def sync_requested(self):
        print("sync requested")
