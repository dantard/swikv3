import json
import os
import subprocess
import sys

from PyQt5 import QtGui
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QMainWindow, QWidget, QVBoxLayout, QApplication, QTreeWidgetItem, QMenu, QFileDialog, QComboBox, QLabel
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


class TreeWidgetApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.api = RCloneApi("gdrive:")

        # Set up the main window
        self.setWindowTitle("QTreeWidget Example")
        self.setGeometry(100, 100, 600, 400)

        # Set up the central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.remotes_cb = QComboBox()
        self.remotes_cb.currentIndexChanged.connect(self.on_remote_changed)

        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["*", "PDF", "Image", "Video", "Audio", "Text", "Archive", "Other"])
        self.filter_cb.currentIndexChanged.connect(self.on_filter_changed)

        tb = self.addToolBar("Main")
        tb.addWidget(QLabel("Remote: "))
        tb.addWidget(self.remotes_cb)
        tb.addSeparator()

        tb.addWidget(QLabel("Filter: "))
        tb.addWidget(self.filter_cb)

        tb.addSeparator()
        tb.addAction("⟳", lambda: self.on_remote_changed(0))
        tb.addSeparator()
        tb.addAction("↓", lambda: self.download_btn_clicked(False))
        tb.addAction("▶", lambda: self.download_btn_clicked(True))

        # Create a QTreeWidget
        self.tree = TreeWidget()
        self.tree.setHeaderLabels(["File", "Size"])
        self.tree.itemExpanded.connect(self.item_expanded)
        self.tree.download_requested.connect(self.download_requested)
        self.tree.doubleClicked.connect(self.on_double_clicked)

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
        layout.addWidget(self.tree)
        QTimer.singleShot(100, self.begin)

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

    def ls(self, path=None, parent1=None):
        self.progressing = Progressing(self, title="Loading...", max_value=0)

        def do_ls():

            res = self.api.ls(path)
            data = json.loads(res)
            for elem in data:

                if self.filter_cb.currentText() == "*" or elem["IsDir"]:
                    pass
                elif self.filter_cb.currentText() == "PDF":
                    if elem["MimeType"] != "application/pdf":
                        continue

                print(elem)
                parent = QTreeWidgetItem(self.tree if parent1 is None else parent1)
                if elem["IsDir"]:
                    parent.setIcon(0, QtGui.QIcon.fromTheme("folder"))
                elif elem["MimeType"] == "application/pdf":
                    parent.setIcon(0, QtGui.QIcon.fromTheme("application-pdf"))
                elif elem["MimeType"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    parent.setIcon(0, QtGui.QIcon.fromTheme("application-msword"))
                elif elem["MimeType"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    parent.setIcon(0, QtGui.QIcon.fromTheme("application-vnd.ms-excel"))
                elif elem["MimeType"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                    parent.setIcon(0, QtGui.QIcon.fromTheme("application-vnd.ms-powerpoint"))
                elif elem["MimeType"] in ["image/jpeg", "image/png", "image/gif", "image/bmp"]:
                    parent.setIcon(0, QtGui.QIcon.fromTheme("image-x-generic"))
                else:
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

                parent.setText(1, text_size)
                parent.path = elem["Name"]
                # parent.setText(1, "[dir]" if elem["IsDir"] else "")

                if elem["IsDir"]:
                    child = QTreeWidgetItem(parent)
                    child.setText(0, "Loading...")
                    child.path = elem["Path"]
            if parent1 is not None:
                parent1.takeChild(0)
            # self.tree.resizeColumnToContents(0)
            # self.tree.resizeColumnToContents(1)
            header = self.tree.header()
            if header:
                header.resizeSection(0, self.width() - 150)

        self.progressing.start(do_ls)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        header = self.tree.header()
        if header:
            header.resizeSection(0, self.width() - 150)

    def download(self, path, where=None, run=False):
        if where is None:
            where = QFileDialog.getExistingDirectory(None, "Save file", path.split("/")[-1])
            if not where:
                return

        self.progressing = Progressing(self, title="Downloading...", max_value=0)

        def do_download():
            self.api.download(path, where)
            self.progressing.close()
            if run:
                os.system("xdg-open '" + where + "/" + path.split("/")[-1] + "' &")
                self.api.run_rclone_command(["xdg-open", ], )

        self.progressing.start(do_download)

    def item_expanded(self, item):
        orig_item = item
        path = item.path
        while item.parent():
            path = item.parent().path + "/" + path
            item = item.parent()

        print("Expanded", path)
        self.ls(path, orig_item)
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TreeWidgetApp()
    window.show()
    sys.exit(app.exec_())
