import sys

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QGraphicsGridLayout, QGraphicsScene, QGraphicsView, QGraphicsWidget, QPushButton, QMainWindow, QSplitter

from LayoutManager import LayoutManager
from renderer import MuPDFRenderer

from GraphView import GraphView
from manager import Manager, Finder
from page import Page
from rubberband import RubberBand


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.hsplitter = QSplitter()


        self.renderer = MuPDFRenderer()
        self.manager = Manager(self.renderer)
        self.view = GraphView(self.manager, self.renderer, LayoutManager.MODE_VERTICAL_MULTIPAGE, page=Page)
        self.view.setWindowTitle("QGraphicsGridLayout Example")
        self.view.setGeometry(100, 100, 400, 300)
        self.manager.set_view(self.view)

        self.renderer.open_pdf("/home/danilo/Desktop/swik-files/Free_Test_Data_10.5MB_PDF.pdf")

        button1 = QPushButton("Button 1", self.hsplitter)
        button1.clicked.connect(self.demo_rubberband)

        self.hsplitter.addWidget(self.view)
        self.setCentralWidget(self.hsplitter)
        self.view.show()

    def demo_rubberband(self):
        finder = Finder(self.view, self.renderer)
        finder.find("nam eget sagittis")


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
