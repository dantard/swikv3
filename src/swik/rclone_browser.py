import json
import os
import subprocess
import sys
from time import sleep

from PyQt5 import QtGui
from PyQt5.QtCore import QTimer, pyqtSignal, QMimeData, Qt
from PyQt5.QtGui import QDrag, QDragLeaveEvent
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

    def copy2(self, src, dest):
        self.src = str(src)
        print("into copy", src, dest)
        self.command = ["rclone", "copy", self.rclone_path + self.src, self.rclone_path + dest]
        print(self.command, "kkk", " ".join(self.command))
        self.run_rclone_command(self.command)
        # os.system(" ".join(self.command))


class RCloneTreeItem(QTreeWidgetItem):
    def __init__(self, parent, elem=None):
        super().__init__(parent)
        self.setText(0, elem["Name"])
        self.path = elem.get("Path")
        self.is_dir = elem.get("IsDir", False)
        self.size = elem.get("Size", -1)
        self.mime_type = elem.get("MimeType")
        if self.is_dir:
            self.setIcon(0, QtGui.QIcon.fromTheme("folder"))
            self.setText(1, "folder")
        elif self.mime_type == "application/pdf":
            self.setIcon(0, QtGui.QIcon.fromTheme("application-pdf"))
            self.setText(1, "pdf")
        elif self.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            self.setIcon(0, QtGui.QIcon.fromTheme("application-msword"))
            self.setText(1, "Word")
        elif self.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            self.setIcon(0, QtGui.QIcon.fromTheme("application-vnd.ms-excel"))
            self.setText(1, "Excel")
        elif self.mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            self.setIcon(0, QtGui.QIcon.fromTheme("application-vnd.ms-powerpoint"))
            self.setText(1, "PowerPoint")
        elif self.mime_type in ["image/jpeg", "image/png", "image/gif", "image/bmp"]:
            self.setIcon(0, QtGui.QIcon.fromTheme("image-x-generic"))
            self.setText(1, self.mime_type.split("/")[-1])
        else:
            self.setText(1, "file")
            self.setIcon(0, QtGui.QIcon.fromTheme("text-x-generic"))

        if self.size == -1:
            text_size = "?"
        elif self.size < 1024:
            text_size = f"{self.size} B"
        elif self.size < 1024 * 1024:
            text_size = f"{self.size / 1024:.2f} KB"
        elif self.size < 1024 * 1024 * 1024:
            text_size = f"{self.size / 1024 / 1024:.2f} MB"
        else:
            text_size = f"{self.size / 1024 / 1024 / 1024:.2f} GB"

        self.setText(2, text_size)


def __lt__(self, other):
    column = self.treeWidget().sortColumn()
    if column == 1:
        if self.is_dir and not other.is_dir:
            return True
        if not self.is_dir and other.is_dir:
            return False
        return self.text(1).lower() < other.text(1).lower()
    elif column == 2:
        return self.size < other.size
    return super().__lt__(other)


def get_absolute_path(self):
    path = self.path
    parent = self.parent()
    while parent:
        path = parent.path + "/" + path
        parent = parent.parent()
    return path


class LoadingItem(RCloneTreeItem):
    def __init__(self, parent):
        super().__init__(parent, {"Name": "Loading..."})


class TreeWidget(QTreeWidget):
    download_requested = pyqtSignal(str)
    move_requested = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.interactable = True
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.aitem = None

    def set_interactable(self, value):
        self.interactable = value

    def startDrag(self, supportedActions):
        super(TreeWidget, self).startDrag(supportedActions)

    def dropEvent(self, a0: QtGui.QDropEvent):
        index = self.indexAt(a0.pos())
        dest_item: RCloneTreeItem = self.itemFromIndex(index)
        source_items = self.selectedItems()
        if dest_item is not None and source_items is not None and dest_item.is_dir:
            a0.acceptProposedAction()
            self.move_requested.emit(source_items, dest_item)
        else:
            a0.ignore()

    # super().dropEvent(a0)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        super().dragLeaveEvent(event)
        self.aitem is not None and self.aitem.setBackground(0, QtGui.QBrush(QtGui.QColor(255, 255, 255)))

    def dragEnterEvent(self, event):
        super().dragEnterEvent(event)
        event.accept()

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        event.accept()

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

        self.emit_enabled = True
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
        self.tree.itemCollapsed.connect(self.item_collapsed)
        self.tree.download_requested.connect(self.download_requested)
        self.tree.move_requested.connect(self.move_requested)
        self.tree.doubleClicked.connect(self.on_double_clicked)
        self.tree.setDragEnabled(True)
        self.tree.setDropIndicatorShown(True)
        # self.tree.setDragDropMode(QAbstractItemView.InternalMove)

        layout.addWidget(tb)
        layout.addWidget(self.tree)
        QTimer.singleShot(100, self.begin)

    def move_requested(self, source_items, dest_item):
        for item in source_items:
            self.copy(item, dest_item)

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
        item: RCloneTreeItem = self.tree.itemFromIndex(index)
        self.download(item.get_absolute_path(), "/tmp", True)

    def download_requested(self, path):
        print("Download requested", path)
        self.download(path)

    def download_btn_clicked(self, run):
        indexes = self.tree.selectedIndexes()
        if indexes:
            for index in indexes:
                if index.isValid():
                    item: RCloneTreeItem = self.tree.itemFromIndex(index)
                    self.download(item.get_absolute_path(), "/tmp" if run else None, run)

    def on_filter_changed(self, index):
        self.on_remote_changed(0)

    def pb_start(self, text=""):
        self.pc_act.setVisible(True)
        self.pb.setFormat(text)
        self.pb.setMaximum(100)
        self.pb.setValue(10)
        # for i in self.protected:
        #    i.setEnabled(False)

    def set_pb_percent(self, value):
        self.pb.setValue(int(value))

    def pb_finish(self):
        self.pb.setValue(100)
        self.pc_act.setVisible(False)
        self.tree.set_interactable(True)
        for i in self.protected:
            i.setEnabled(True)

    def copy(self, source_item, dest_item):
        self.pb_start("Copying...")
        if dest_item.is_dir:
            dest_dir = dest_item.get_absolute_path()
        else:
            dest_dir = os.path.dirname(dest_item.get_absolute_path())

        self.api.copy2(source_item.get_absolute_path(), dest_dir)
        self.tree.blockSignals(True)
        # self.emit_enabled = False
        dest_item.takeChildren()
        LoadingItem(dest_item)
        # self.emit_enabled = True
        self.tree.blockSignals(False)

        self.ls(dest_item.get_absolute_path(), dest_item)

    def ls(self, path=None, parent1=None):
        self.pb_start("Loading...")

        def do_ls():
            print("do ls", path)
            res = self.api.ls(path)
            try:
                data = json.loads(res)
            except:
                return

            data.sort(key=lambda x: not x["IsDir"])

            for elem in data:
                self.set_pb_percent(100 * data.index(elem) / len(data))

                parent = RCloneTreeItem(parent1 if parent1 else self.tree, elem)

                if parent.is_dir:
                    LoadingItem(parent)

            if parent1 is not None:
                parent1.takeChild(0)

            header = self.tree.header()
            if header:
                header.resizeSection(0, self.width() - 250)
                self.tree.resizeColumnToContents(1)
                self.tree.resizeColumnToContents(2)

            self.tree.sortByColumn(1, Qt.AscendingOrder)
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
        if self.emit_enabled:
            path = item.get_absolute_path()
            print("putoexpanded")
            self.ls(path, item)

    def item_collapsed(self, item):
        item.takeChildren()
        item.addChild(LoadingItem(item))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        widget = QWidget()
        self.setCentralWidget(widget)
        widget.setLayout(QHBoxLayout())
        self.browser1 = RCloneBrowser()
        #        self.browser2.set_accept_drops(True)
        widget.layout().addWidget(self.browser1)
        # widget.layout().addWidget(self.browser2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
