from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QComboBox

from GraphView import GraphView
from LayoutManager import LayoutManager
from toolbars.toolbar import Toolbar


class ZoomToolbar(Toolbar):
    options = ["25%", "50%", "100%", "200%", "300%", "400%", "500%", "Fit Width"]

    def __init__(self, view: GraphView, toolbar: QToolBar = None):
        super().__init__(view, toolbar)

        self.toolbar.addSeparator()
        self.toolbar.addAction("Zoom Out", lambda: self.zoom(self.view.get_ratio() - 0.1)).setIcon(QIcon(":/icons/zoom-out.png"))

        self.lb_zoom = QComboBox()
        self.lb_zoom.addItems(self.options)
        self.lb_zoom.setCurrentText("{}%".format(int(self.view.get_ratio() * 100)))
        self.lb_zoom.setMaximumWidth(120)
        self.lb_zoom.setEditable(True)
        self.lb_zoom.activated.connect(self.option_selected)
        self.lb_zoom.lineEdit().returnPressed.connect(self.zoom_entered)

        self.toolbar.addWidget(self.lb_zoom)
        self.toolbar.addAction("Zoom In", lambda: self.zoom(self.view.get_ratio() + 0.1)).setIcon(QIcon(":/icons/zoom-in.png"))

        self.view.ratio_changed.connect(self.ratio_changed)

    def option_selected(self):
        if self.lb_zoom.currentText() == "Fit Width":
            self.view.layout_manager.set_mode(LayoutManager.MODE_FIT_WIDTH)
            self.lb_zoom.setEditable(False)
        else:
            self.view.layout_manager.set_mode(LayoutManager.MODE_VERTICAL)
            self.view.set_ratio(float(self.lb_zoom.currentText().replace("%", "")) / 100, False)
            self.lb_zoom.setEditable(True)

    def zoom_entered(self):

        self.lb_zoom.blockSignals(True)
        self.lb_zoom.removeItem(self.lb_zoom.count() - 1)
        self.lb_zoom.blockSignals(False)

        if self.lb_zoom.currentText().replace("%", "").isnumeric():
            self.zoom(float(self.lb_zoom.currentText().replace("%", "")) / 100)
        else:
            self.zoom(self.view.get_ratio())

    def setEnabled(self, value):
        self.lb_zoom.setEnabled(value)
        self.setButtonsEnabled(["Zoom In", "Zoom Out"], value)

    def zoom(self, value):
        self.view.set_ratio(value, True)

    def ratio_changed(self, ratio):

        if ratio < 0:
            self.lb_zoom.blockSignals(True)
            self.lb_zoom.setEditable(False)
            self.lb_zoom.setCurrentText("Fit Width")
            self.lb_zoom.blockSignals(False)
        else:
            self.lb_zoom.blockSignals(True)
            self.lb_zoom.setEditable(True)
            self.lb_zoom.setCurrentText("{}%".format(int(ratio * 100)))
            self.lb_zoom.blockSignals(False)
