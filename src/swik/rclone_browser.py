import json
import os
import subprocess
import sys
from time import sleep

from PyQt5 import QtGui
from PyQt5.QtCore import QTimer, pyqtSignal, QMimeData, Qt
from PyQt5.QtGui import QDrag, QDragLeaveEvent
from PyQt5.QtWidgets import QTreeWidget, QMainWindow, QWidget, QVBoxLayout, QApplication, QTreeWidgetItem, QMenu, QFileDialog, QComboBox, QLabel, QToolBar, \
    QProgressBar, QAbstractItemView, QHBoxLayout, QProgressDialog


class Progressing(QProgressDialog):
    done = pyqtSignal(object)

    def __init__(self, parent, max_value=0, title=None, cancel=False):
        super().__init__(parent)
        self.setMaximum(max_value)
        self.callback = None
        self.setLabelText(title)
        if not cancel:
            self.setCancelButton(None)
        self.show()

    def set_progress(self, value):
        self.setValue(int(value))
        QApplication.processEvents()
        return not self.wasCanceled()

    def run(self):
        self.ret_value = self.func(*self.args)
        self.done.emit(self.ret_value)
        if self.callback:
            self.callback(self.ret_value, *self.args)
        self.hide()

    def get_return_value(self):
        return self.ret_value

    def start(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.callback = kwargs.get("callback", None)
        QTimer.singleShot(50, self.run)


class RCloneApi:

    def __init__(self, rclone_path):
        self.rclone_path = rclone_path

    def set_remote(self, remote):
        self.rclone_path = remote

    def ls(self, path=None):
        command = ["rclone", "lsjson", self.rclone_path + (path if path else "")]
        return self.run_rclone_command(command)

    def run_rclone_command(self, command):
        print("*** Running command: ", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None
        print("done")
        return result.stdout

    def download(self, path, where):
        command = ["rclone", "copy", self.rclone_path + path, where]
        return self.run_rclone_command(command)

    def list_remotes(self):
        command = ["rclone", "listremotes"]
        return self.run_rclone_command(command)

    def copy2(self, src, dest):
        command = ["rclone", "copy", self.rclone_path + src, self.rclone_path + dest]
        self.run_rclone_command(command)

    def delete(self, path):
        command = ["rclone", "delete", self.rclone_path + path]
        self.run_rclone_command(command)


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
            if self.is_dir and other.is_dir:
                return self.text(0).lower() < other.text(0).lower()
            elif self.is_dir and not other.is_dir:
                return True
            elif not self.is_dir and other.is_dir:
                return False
            elif self.text(1).lower() != other.text(1).lower():
                return self.text(1).lower() < other.text(1).lower()
            return self.text(0).lower() < other.text(0).lower()

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
    download_requested = pyqtSignal(object)
    move_requested = pyqtSignal(object, object)
    delete_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.interactable = True
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
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
            self.move_requested.emit(source_items, dest_item)

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

                # item = self.itemFromIndex(index)

                menu = QMenu()
                download = menu.addAction("Download")
                delete = menu.addAction("Delete")
                res = menu.exec_(self.viewport().mapToGlobal(a0.pos()))
                selected = self.selectedItems()

                if res == download:
                    self.download_requested.emit(selected)
                elif res == delete:
                    self.delete_requested.emit(selected)


class RCloneBrowser(QWidget):
    def __init__(self):
        super().__init__()

        self.emit_enabled = True
        self.api = RCloneApi("")

        # Set up the main window
        self.setWindowTitle("QTreeWidget Example")
        self.setGeometry(100, 100, 600, 400)

        # Set up the central widget and layout
        layout = QVBoxLayout(self)

        # Create a QTreeWidget
        self.tree = TreeWidget()
        self.tree.setHeaderLabels(["File", "Type", "Size"])
        self.tree.itemExpanded.connect(self.item_expanded)
        self.tree.itemCollapsed.connect(self.item_collapsed)
        self.tree.download_requested.connect(self.download_requested)
        self.tree.delete_requested.connect(self.delete_requested)
        self.tree.move_requested.connect(self.copy_requested)
        self.tree.doubleClicked.connect(self.on_double_clicked)
        self.tree.setDragEnabled(True)
        self.tree.setDropIndicatorShown(True)
        # self.tree.setDragDropMode(QAbstractItemView.InternalMove)

        layout.addWidget(self.tree)
        layout.setContentsMargins(0, 0, 0, 0)

        remotes = self.api.list_remotes().split("\n")
        remotes = [remote for remote in remotes if remote != ""]

        # self.api.set_remote(self.remotes_cb.currentText())
        for remote in remotes:
            rem = RCloneTreeItem(self.tree, {"Name": remote, "IsDir": True, "Path": remote})
            LoadingItem(rem)
        self.tree.sortByColumn(1, Qt.AscendingOrder)

    def copy_requested(self, source_items, dest_item):
        self.copy(source_items, dest_item)

    def set_accept_drops(self, value):
        self.tree.viewport().setAcceptDrops(value)

    def begin(self):
        res = self.api.list_remotes()
        remotes = res.split("\n")
        remotes = [remote for remote in remotes if remote != ""]
        self.remotes_cb.addItems(remotes)

    def on_double_clicked(self, index):
        item: RCloneTreeItem = self.tree.itemFromIndex(index)
        self.download([item], "/tmp", True)

    def download_requested(self, items):
        print("Download requested", items)
        self.download(items)

    def delete_requested(self, items):
        print("Delete requested", items)
        self.delete(items)

    def download_btn_clicked(self, run):
        indexes = self.tree.selectedIndexes()
        if indexes:
            for index in indexes:
                if index.isValid():
                    item: RCloneTreeItem = self.tree.itemFromIndex(index)
                    self.download(item.get_absolute_path(), "/tmp" if run else None, run)

    def on_filter_changed(self, index):
        self.on_remote_changed(0)

    def copy(self, items, dest_item):
        self.pd = Progressing(self, len(items), "Copying...", cancel=True)

        def do_copy():
            if dest_item.is_dir:
                dest_dir = dest_item.get_absolute_path()
            else:
                dest_dir = os.path.dirname(dest_item.get_absolute_path())

            for source_item in items:
                if self.pd.wasCanceled():
                    break
                self.pd.setLabelText("Copying " + source_item.get_absolute_path())
                self.pd.set_progress(items.index(source_item))
                QApplication.processEvents()
                self.api.copy2(source_item.get_absolute_path(), dest_dir)

            self.pd.setValue(len(items))

            self.tree.blockSignals(True)
            dest_item.takeChildren()
            LoadingItem(dest_item)
            self.ls(dest_item.get_absolute_path(), dest_item)
            self.tree.blockSignals(False)

        self.pd.start(do_copy)

    def ls(self, path=None, parent1=None):
        self.pd = Progressing(self, 0, "Listing " + path)

        def do_ls():

            res = self.api.ls(path)
            data = json.loads(res)

            if parent1 is not None:
                self.remove_loading(parent1)

            for elem in data:
                parent = RCloneTreeItem(parent1 if parent1 else self.tree, elem)

                if parent.is_dir:
                    LoadingItem(parent)

            header = self.tree.header()
            if header:
                header.resizeSection(0, self.width() - 250)
                self.tree.resizeColumnToContents(1)
                self.tree.resizeColumnToContents(2)

            self.tree.sortByColumn(1, Qt.AscendingOrder)
            self.pd.close()

        self.pd.start(do_ls)

    def remove_loading(self, parent1):
        for i in range(parent1.childCount()):
            if isinstance(parent1.child(i), LoadingItem):
                parent1.takeChild(i)
                break

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        header = self.tree.header()
        if header:
            header.resizeSection(0, self.width() - 250)
            self.tree.resizeColumnToContents(1)
            self.tree.resizeColumnToContents(2)

    def delete(self, items):
        self.pd = Progressing(self, len(items), "Deleting", cancel=True)

        def do_download():
            parents = [item.parent() for item in items]
            for item in items:
                if self.pd.wasCanceled():
                    break
                self.pd.setValue(items.index(item))
                path = item.get_absolute_path()
                self.api.delete(path)

            self.pd.setValue(len(items))

            self.tree.blockSignals(True)
            for parent in parents:
                parent.takeChildren()
                LoadingItem(parent)
                self.ls(parent.get_absolute_path(), parent)
            self.tree.blockSignals(False)

        self.pd.start(do_download)

    def download(self, items, where=None, run=False):
        if where is None:
            where = QFileDialog.getExistingDirectory(None, "Save file", "", QFileDialog.ShowDirsOnly)
            if not where:
                return

        self.pd = Progressing(self, len(items), "Downloading", cancel=True)

        def do_download():
            for item in items:
                if self.pd.wasCanceled():
                    break
                self.pd.setLabelText("Downloading " + item.get_absolute_path())
                self.pd.setValue(items.index(item))

                path = item.get_absolute_path()
                if item.is_dir:
                    self.api.download(path, where + "/" + path.split("/")[-1])
                else:
                    self.api.download(path, where)

            self.pd.close()

            if run:
                os.system("xdg-open '" + where + "/" + items[0].get_absolute_path().split("/")[-1] + "' &")
                self.api.run_rclone_command(["xdg-open", ], )

        self.pd.start(do_download)

    def item_expanded(self, item):
        item.takeChildren()
        path = item.get_absolute_path()
        self.ls(path, item)

    def item_collapsed(self, item):
        pass
        # item.takeChildren()
        # item.addChild(LoadingItem(item))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        widget = QWidget()
        self.setCentralWidget(widget)
        widget.setLayout(QHBoxLayout())
        self.browser1 = RCloneBrowser()
        #        self.browser2.set_accept_drops(True)
        widget.layout().addWidget(self.browser1)
        self.setGeometry(100, 100, 600, 400)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
