import json
import os
import subprocess
import sys
from time import sleep

from PyQt5 import QtGui
from PyQt5.QtCore import QTimer, pyqtSignal, QMimeData, Qt
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QTreeWidget, QMainWindow, QWidget, QVBoxLayout, QApplication, QTreeWidgetItem, QMenu, QFileDialog, QComboBox, QLabel, QToolBar, \
    QProgressBar, QAbstractItemView, QHBoxLayout
from swik.progressing import Progressing


class RCloneApi:

    def __init__(self, rclone_path):
        self.rclone_path = rclone_path

    def set_remote(self, remote):
        self.rclone_path = remote

    def ls(self, path=None):
        command = ["rclone", "lsjson", self.rclone_path + (path if path else "")]
        return self.run_rclone_command(command)

    def run_rclone_command(self, command):
        """Runs an rclone command and returns the output."""
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None
        return result.stdout

    def download(self, path, where):
        command = ["rclone", "copy", self.rclone_path + path, where]
        return self.run_rclone_command(command)

    def list_remotes(self):
        command = ["rclone", "listremotes"]
        return self.run_rclone_command(command)


class TreeWidget(QTreeWidget):
    download_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.interactable = True
        self.setSortingEnabled(True)
        self.setDragEnabled(True)

    def dropEvent(self, a0: QtGui.QDropEvent):
        print("dropEvent", a0.proposedAction(), a0.mimeData().text())
        super().dropEvent(a0)

    def dragEnterEvent(self, event):
        super().dragEnterEvent(event)
        event.accept()

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        event.accept()

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            mimeData = QMimeData()
            mimeData.setText(item.text(0))
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec_(Qt.MoveAction)

    def set_interactable(self, value):
        self.interactable = value

    def mousePressEvent(self, e):
        if not self.interactable:
            return
        super().mousePressEvent(e)

    def contextMenuEvent(self, a0: QtGui.QContextMenuEvent) -> None:
        print("contextMenuEvent")
        super().contextMenuEvent(a0)
        indexes = self.selectedIndexes()
        if indexes:
            index = self.indexAt(a0.pos())
            if index.isValid():

                item = self.itemFromIndex(index)
                path = item.path
                while item.parent():
                    path = item.parent().path + "/" + path
                    item = item.parent()

                menu = QMenu()
                download = menu.addAction("Download")
                res = menu.exec_(self.viewport().mapToGlobal(a0.pos()))
                if res == download:
                    self.download_requested.emit(path)


class RCloneBrowser(QWidget):
    def __init__(self):
        super().__init__()

        self.api = RCloneApi("gdrive:")

        # Set up the main window
        self.setWindowTitle("QTreeWidget Example")
        self.setGeometry(100, 100, 600, 400)

        # Set up the central widget and layout
        layout = QVBoxLayout(self)

        self.remotes_cb = QComboBox()
        self.remotes_cb.currentIndexChanged.connect(self.on_remote_changed)

        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["*", "PDF", "Image", "Video", "Audio", "Text", "Archive", "Other"])
        self.filter_cb.currentIndexChanged.connect(self.on_filter_changed)
        self.pb = QProgressBar()

        self.protected = []

        tb = QToolBar("Main")
        tb.addWidget(QLabel("Remote: "))
        self.protected.append(tb.addWidget(self.remotes_cb))
        tb.addSeparator()

        tb.addWidget(QLabel("Filter: "))
        self.protected.append(tb.addWidget(self.filter_cb))

        tb.addSeparator()
        self.protected.append(tb.addAction("⟳", lambda: self.on_remote_changed(0)))
        tb.addSeparator()
        self.protected.append(tb.addAction("↓", lambda: self.download_btn_clicked(False)))
        self.protected.append(tb.addAction("▶", lambda: self.download_btn_clicked(True)))

        self.pc_act = tb.addWidget(self.pb)

        # Create a QTreeWidget
        self.tree = TreeWidget()
        self.tree.setHeaderLabels(["File", "Type", "Size"])
        self.tree.itemExpanded.connect(self.item_expanded)
        self.tree.download_requested.connect(self.download_requested)
        self.tree.doubleClicked.connect(self.on_double_clicked)
        self.tree.setDragEnabled(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)

        # Add some items to the tree
        # for i in range(5):
        #     parent = QTreeWidgetItem(self.tree)
        #     parent.setText(0, f"Parent {i}")
        #     parent.setText(1, f"Parent {i} Value")
        #     for j in range(3):
        #         child = QTreeWidgetItem(parent)
        #         child.setText(0, f"Child {i}-{j}")
        #         child.setText(1, f"Child {i}-{j} Value")

        # Add the tree widget to the layout
        layout.addWidget(tb)
        layout.addWidget(self.tree)
        QTimer.singleShot(100, self.begin)

    def set_accept_drops(self, value):
        self.tree.viewport().setAcceptDrops(value)

    def begin(self):
        res = self.api.list_remotes()
        remotes = res.split("\n")
        remotes = [remote for remote in remotes if remote != ""]
        self.remotes_cb.addItems(remotes)

    def on_remote_changed(self, index):
        self.tree.clear()
        self.api.set_remote(self.remotes_cb.currentText())
        self.ls()

    def on_double_clicked(self, index):
        item = self.tree.itemFromIndex(index)
        path = item.path
        while item.parent():
            path = item.parent().path + "/" + path
            item = item.parent()
        self.download(path, "/tmp", True)

    def download_requested(self, path):
        print("Download requested", path)
        self.download(path)

    def download_btn_clicked(self, run):
        indexes = self.tree.selectedIndexes()
        if indexes:
            index = indexes[0]
            if index.isValid():
                item = self.tree.itemFromIndex(index)
                path = item.path
                while item.parent():
                    path = item.parent().path + "/" + path
                    item = item.parent()
                if run:
                    self.download(path, "/tmp", run)
                else:
                    self.download(path, None, run)

    def on_filter_changed(self, index):
        self.on_remote_changed(0)

    def pb_start(self, text=""):
        self.pc_act.setVisible(True)
        self.pb.setFormat(text)
        self.pb.setMaximum(100)
        self.pb.setValue(10)
        for i in self.protected:
            i.setEnabled(False)

    def set_pb_percent(self, value):
        self.pb.setValue(int(value))

    def pb_finish(self):
        self.pb.setValue(100)
        self.pc_act.setVisible(False)
        self.tree.set_interactable(True)
        for i in self.protected:
            i.setEnabled(True)

    def ls(self, path=None, parent1=None):
        self.pb_start("Loading...")

        def do_ls():

            res = self.api.ls(path)
            try:
                data = json.loads(res)
            except:
                QTimer.singleShot(100, do_ls)
                return

            data.sort(key=lambda x: not x["IsDir"])
            for elem in data:
                self.set_pb_percent(100 * data.index(elem) / len(data))

                if self.filter_cb.currentText() == "*" or elem["IsDir"]:
                    pass
                elif self.filter_cb.currentText() == "PDF":
                    if elem["MimeType"] != "application/pdf":
                        continue

                print(elem)
                parent = QTreeWidgetItem(self.tree if parent1 is None else parent1)
                parent.setText(1, "dir")
                if elem["IsDir"]:
                    parent.setIcon(0, QtGui.QIcon.fromTheme("folder"))
                elif elem["MimeType"] == "application/pdf":
                    parent.setIcon(0, QtGui.QIcon.fromTheme("application-pdf"))
                    parent.setText(1, "pdf")
                elif elem["MimeType"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    parent.setIcon(0, QtGui.QIcon.fromTheme("application-msword"))
                    parent.setText(1, "Word")
                elif elem["MimeType"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    parent.setIcon(0, QtGui.QIcon.fromTheme("application-vnd.ms-excel"))
                    parent.setText(1, "Excel")
                elif elem["MimeType"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                    parent.setIcon(0, QtGui.QIcon.fromTheme("application-vnd.ms-powerpoint"))
                    parent.setText(1, "PowerPoint")
                elif elem["MimeType"] in ["image/jpeg", "image/png", "image/gif", "image/bmp"]:
                    parent.setIcon(0, QtGui.QIcon.fromTheme("image-x-generic"))
                    parent.setText(1, elem["MimeType"].split("/")[-1])
                else:
                    parent.setText(1, "file")
                    parent.setIcon(0, QtGui.QIcon.fromTheme("text-x-generic"))

                parent.setText(0, elem["Name"])
                size = elem.get("Size")
                if size == -1:
                    text_size = "?"
                elif size < 1024:
                    text_size = f"{size} B"
                elif size < 1024 * 1024:
                    text_size = f"{size / 1024:.2f} KB"
                elif size < 1024 * 1024 * 1024:
                    text_size = f"{size / 1024 / 1024:.2f} MB"
                else:
                    text_size = f"{size / 1024 / 1024 / 1024:.2f} GB"

                parent.setText(2, text_size)
                parent.path = elem["Name"]
                # parent.setText(1, "[dir]" if elem["IsDir"] else "")

                if elem["IsDir"]:
                    child = QTreeWidgetItem(parent)
                    child.setText(0, "Loading...")
                    child.path = elem["Path"]
            if parent1 is not None:
                parent1.takeChild(0)

            header = self.tree.header()
            if header:
                header.resizeSection(0, self.width() - 250)
                self.tree.resizeColumnToContents(1)
                self.tree.resizeColumnToContents(2)
            self.pb_finish()

        QTimer.singleShot(100, do_ls)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        header = self.tree.header()
        if header:
            header.resizeSection(0, self.width() - 250)
            self.tree.resizeColumnToContents(1)
            self.tree.resizeColumnToContents(2)

    def download(self, path, where=None, run=False):
        if where is None:
            where = QFileDialog.getExistingDirectory(None, "Save file", path.split("/")[-1])
            if not where:
                return

        self.pb_start("Downloading...")

        def do_download():
            self.api.download(path, where)
            self.pb_finish()
            if run:
                os.system("xdg-open '" + where + "/" + path.split("/")[-1] + "' &")
                self.api.run_rclone_command(["xdg-open", ], )

        QTimer.singleShot(100, do_download)

    def item_expanded(self, item):
        orig_item = item
        path = item.path
        while item.parent():
            path = item.parent().path + "/" + path
            item = item.parent()

        print("Expanded", path)
        self.ls(path, orig_item)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        widget = QWidget()
        self.setCentralWidget(widget)
        widget.setLayout(QHBoxLayout())
        self.browser1 = RCloneBrowser()
        self.browser2 = RCloneBrowser()
        self.browser2.set_accept_drops(True)
        widget.layout().addWidget(self.browser1)
        widget.layout().addWidget(self.browser2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
