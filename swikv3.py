import sys

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QGraphicsGridLayout, QGraphicsScene, QGraphicsView, QGraphicsWidget, QPushButton, QMainWindow, QSplitter

from LayoutManager import LayoutManager
from Renderer import MuPDFRenderer

from GraphView import GraphView
from manager import Manager
from rubberband import RubberBand


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.hsplitter = QSplitter()
        self.manager = Manager()

        renderer = MuPDFRenderer()
        self.view = GraphView(self.manager, renderer, LayoutManager.MODE_VERTICAL_MULTIPAGE)
        self.view.setWindowTitle("QGraphicsGridLayout Example")
        self.view.setGeometry(100, 100, 400, 300)
        renderer.open_pdf("/home/danilo/08-Lugar de las raíces I.pdf")

        button1 = QPushButton("Button 1", self.hsplitter)
        button1.clicked.connect(self.demo_rubberband)

        self.hsplitter.addWidget(self.view)
        self.setCentralWidget(self.hsplitter)
        self.view.show()




    def demo_rubberband(self):
        self.rb = RubberBand(self.view)
        self.view.scene().addItem(self.rb)


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()




if __name__ == "__main__":
    main()
