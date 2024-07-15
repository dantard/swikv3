import json
import os
import re
import subprocess
import sys
import threading
import time
from time import sleep
from typing import Tuple, Union, Dict, Any

from PyQt5 import QtGui
from PyQt5.QtCore import QTimer, pyqtSignal, QMimeData, Qt, QUrl, QObject
from PyQt5.QtGui import QDrag, QDragLeaveEvent
from PyQt5.QtWidgets import QTreeWidget, QMainWindow, QWidget, QVBoxLayout, QApplication, QTreeWidgetItem, QMenu, QFileDialog, QComboBox, QLabel, QToolBar, \
    QProgressBar, QAbstractItemView, QHBoxLayout, QProgressDialog, QMessageBox, QInputDialog


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

    def run_rclone_command2(self, command):
        command.append("-P")
        print("*** Running command2: ", " ".join(command))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process

    def download(self, path, where):
        command = ["rclone", "copy", self.rclone_path + path, where]
        return self.run_rclone_command(command)

    def list_remotes(self):
        command = ["rclone", "listremotes"]
        return self.run_rclone_command(command)

    def copy2(self, src, dest):
        command = ["rclone", "copy", self.rclone_path + src, self.rclone_path + dest]
        return self.run_rclone_command2(command)

    def delete(self, path, purge=False):
        if purge:
            command = ["rclone", "purge", self.rclone_path + path]
        else:
            command = ["rclone", "delete", self.rclone_path + path]
        self.run_rclone_command(command)

    def mkdir(self, path):
        command = ["rclone", "mkdir", self.rclone_path + path]
        self.run_rclone_command(command)

    def move(self, src, dest):
        command = ["rclone", "move", self.rclone_path + src, self.rclone_path + dest]
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
    copy_requested = pyqtSignal(object, object)
    move_requested = pyqtSignal(object, object)

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
        mimeData = QMimeData()
        str = "*".join([item.get_absolute_path() for item in self.selectedItems()])
        mimeData.setData("application/rclone-browser", str.encode("utf-8"))
        # mimeData.setData("text/plain", str.encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec(supportedActions)

    def dropEvent(self, a0: QtGui.QDropEvent):

        index = self.indexAt(a0.pos())
        dest_item: RCloneTreeItem = self.itemFromIndex(index)
        dest_item.setBackground(0, QtGui.QBrush(QtGui.QColor(255, 255, 255)))

        if a0.mimeData().hasFormat("application/rclone-browser"):
            source = a0.mimeData().data("application/rclone-browser").data().decode("utf-8")
            source_items = source.split("*")

            print("here", a0.keyboardModifiers())

            if len(source_items) > 0 and dest_item is not None and dest_item.is_dir:
                if a0.keyboardModifiers() == Qt.AltModifier:
                    self.move_requested.emit(source_items, dest_item)
                else:
                    self.copy_requested.emit(source_items, dest_item)

        elif a0.mimeData().hasUrls():
            urls = a0.mimeData().urls()
            source_paths = [url.toLocalFile() for url in urls]
            self.copy_requested.emit(source_paths, dest_item)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        super().dragLeaveEvent(event)
        if self.aitem is not None:
            self.aitem is not None and self.aitem.setBackground(0, QtGui.QBrush(QtGui.QColor(255, 255, 255)))

    def dragEnterEvent(self, event):
        super().dragEnterEvent(event)
        event.accept()
        print("dragEnterEvent")

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        if self.aitem is not None:
            self.aitem.setBackground(0, QtGui.QBrush(QtGui.QColor(255, 255, 255)))

        index = self.indexAt(event.pos())
        dest_item: RCloneTreeItem = self.itemFromIndex(index)
        if dest_item is not None and dest_item.is_dir:
            event.accept()
        else:
            event.ignore()
            return

        if self.aitem is not None:
            dest_item.setBackground(0, QtGui.QBrush(QtGui.QColor(255, 0, 0)))

        self.aitem = dest_item

    def mousePressEvent(self, e):
        if not self.interactable:
            return
        super().mousePressEvent(e)


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
        self.tree.copy_requested.connect(self.copy_requested)
        self.tree.move_requested.connect(self.move_requested)
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

    def copy_requested(self, source_paths, dest_item):
        print("Copy requested", source_paths, dest_item)
        self.copy(source_paths, dest_item)

    def move_requested(self, source_paths, dest_item):
        self.pd = Progressing(self, len(source_paths), "Moving...", cancel=True)

        def do_move():
            if dest_item.is_dir:
                dest_dir = dest_item.get_absolute_path()
            else:
                dest_dir = os.path.dirname(dest_item.get_absolute_path())

            for source_path in source_paths:

                if self.pd.wasCanceled():
                    break
                self.pd.setLabelText("Moving " + source_path)
                self.pd.set_progress(source_paths.index(source_path))
                QApplication.processEvents()
                self.api.move(source_path, dest_dir)
            self.pd.setValue(len(source_paths))
            self.update_item(dest_item)

            for source_path in source_paths:
                dir = os.path.dirname(source_path)
                source_item = self.get_item_from_absolute_path(dir)
                if source_item is not None:
                    self.update_item(source_item)

        self.pd.start(do_move)

    def get_item_from_absolute_path(self, path) -> RCloneTreeItem:
        bits = path.split("/")
        parent = self.tree.invisibleRootItem()
        while len(bits) > 0:
            bit = bits.pop(0)
            for i in range(parent.childCount()):
                if parent.child(i).text(0) == bit:
                    parent = parent.child(i)
                    break
            else:
                return None

        return parent

    def update_item(self, item: RCloneTreeItem):
        self.tree.blockSignals(True)
        item.takeChildren()
        LoadingItem(item)
        self.ls(item.get_absolute_path(), item)
        self.tree.blockSignals(False)

    def set_accept_drops(self, value):
        self.tree.viewport().setAcceptDrops(value)

    def on_double_clicked(self, index):
        item: RCloneTreeItem = self.tree.itemFromIndex(index)
        if item.is_dir:
            item.setExpanded(not item.isExpanded())
        else:
            self.download([item], "/tmp", True)

    def download_btn_clicked(self, run):
        indexes = self.tree.selectedIndexes()
        if indexes:
            for index in indexes:
                if index.isValid():
                    item: RCloneTreeItem = self.tree.itemFromIndex(index)
                    self.download(item.get_absolute_path(), "/tmp" if run else None, run)

    def copy(self, source_paths, dest_item):
        self.pd = Progressing(self, 100, "Copying...", cancel=True)
        self.timer = QTimer()
        processes = []

        def update_view():
            self.tree.blockSignals(True)
            dest_item.takeChildren()
            LoadingItem(dest_item)
            self.ls(dest_item.get_absolute_path(), dest_item)
            self.tree.blockSignals(False)

        def do_copy():
            if dest_item.is_dir:
                dest_dir = dest_item.get_absolute_path()
            else:
                dest_dir = os.path.dirname(dest_item.get_absolute_path())

            for source_path in source_paths:
                if self.pd.wasCanceled():
                    break
                self.pd.setLabelText("Copying " + source_path)
                QApplication.processEvents()
                process = self.api.copy2(source_path, dest_dir)
                processes.append(process)
            self.timer.start(100)

        def check_processes():  # self.pd.setValue(len(source_paths))
            progress = {}
            for process in processes:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    ok, data = extract_rclone_progress(output)
                    if ok:
                        progress[process] = data['progress']

            if len(progress) > 0:
                avg = int(sum(list(progress.values())) / len(progress))
                self.pd.setValue(avg)

            if all([process.poll() is not None for process in processes]):
                self.timer.stop()
                self.pd.close()
                update_view()

        self.timer.timeout.connect(check_processes)
        self.pd.start(do_copy)

    def new_dir(self, item, name):
        self.pd = Progressing(self, 0, "Creating " + name)

        def do_mkdir():
            self.api.mkdir(item.get_absolute_path() + os.sep + name)
            self.pd.close()

            self.tree.blockSignals(True)
            item.takeChildren()
            LoadingItem(item)
            self.ls(item.get_absolute_path(), item)
            self.tree.blockSignals(False)

        self.pd.start(do_mkdir)

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

        def do_delete():
            helper, parents = [], []
            for item in items:
                if item.parent().path not in helper:
                    helper.append(item.parent().path)
                    parents.append(item.parent())

            for item in items:
                if self.pd.wasCanceled():
                    break
                self.pd.setValue(items.index(item))
                path = item.get_absolute_path()
                self.api.delete(path, item.is_dir)

            self.pd.setValue(len(items))

            self.tree.blockSignals(True)
            for parent in parents:
                parent.takeChildren()
                LoadingItem(parent)
                self.ls(parent.get_absolute_path(), parent)
            self.tree.blockSignals(False)

        self.pd.start(do_delete)

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

    def contextMenuEvent(self, a0: QtGui.QContextMenuEvent) -> None:
        print("contextMenuEvent")
        super().contextMenuEvent(a0)
        indexes = self.tree.selectedIndexes()
        if indexes:
            pos = self.tree.mapFrom(self, a0.pos())
            index = self.tree.indexAt(pos)
            if index.isValid():

                # item = self.itemFromIndex(index)

                menu = QMenu()
                download = menu.addAction("Download")
                new_dir, refresh = [-1] * 2

                if len(self.tree.selectedItems()) == 1 and self.tree.selectedItems()[0].is_dir:
                    new_dir = menu.addAction("New Folder")
                    menu.addSeparator()
                    refresh = menu.addAction("Refresh")

                menu.addSeparator()
                delete = menu.addAction("Delete")

                res = menu.exec_(a0.globalPos())

                selected = self.tree.selectedItems()

                if res == download:
                    self.download(selected)
                elif res == delete:
                    if QMessageBox.question(self, "Delete",
                                            "Are you sure you want to delete these items?",
                                            QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                        self.delete(selected)
                elif res == new_dir:
                    text, ok = QInputDialog.getText(self, "New Folder", "Enter the name of the new folder:")
                    if ok:
                        self.new_dir(selected[0], text)
                elif res == refresh:
                    self.update_item(selected[0])


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


def extract_rclone_progress(buffer: str) -> Tuple[bool, Union[Dict[str, Any], None]]:
    # matcher that checks if the progress update block is completely buffered yet (defines start and stop)
    # it gets the sent bits, total bits, progress, transfer-speed and eta
    reg_transferred = re.findall(
        r"Transferred:\s+(\d+.\d+ \w+) \/ (\d+.\d+ \w+), (\d{1,3})%, (\d+.\d+ \w+\/\w+), ETA (\S+)",
        buffer,
    )

    if reg_transferred:  # transferred block is completely buffered
        # get the progress of the individual files
        # matcher gets the currently transferring files and their individual progress
        # returns list of tuples: (name, progress, file_size, unit)
        prog_transferring = []
        prog_regex = re.findall(
            r"\* +(.+):[ ]+(\d{1,3})% \/(\d+.\d+)([a-zA-Z]+),", buffer
        )
        for item in prog_regex:
            prog_transferring.append(
                (
                    item[0],
                    int(item[1]),
                    float(item[2]),
                    # the suffix B of the unit is missing for subprocesses
                    item[3] + "B",
                )
            )

        out = {"prog_transferring": prog_transferring}
        sent_bits, total_bits, progress, transfer_speed_str, eta = reg_transferred[0]
        out["progress"] = float(progress.strip())
        out["total_bits"] = float(re.findall(r"\d+.\d+", total_bits)[0])
        out["sent_bits"] = float(re.findall(r"\d+.\d+", sent_bits)[0])
        out["unit_sent"] = re.findall(r"[a-zA-Z]+", sent_bits)[0]
        out["unit_total"] = re.findall(r"[a-zA-Z]+", total_bits)[0]
        out["transfer_speed"] = float(re.findall(r"\d+.\d+", transfer_speed_str)[0])
        out["transfer_speed_unit"] = re.findall(
            r"[a-zA-Z]+/[a-zA-Z]+", transfer_speed_str
        )[0]
        out["eta"] = eta

        return True, out

    else:
        return False, None


#
#
# def real_time():
#     import subprocess
#
#     # Define the external command to run
#     command = ["rclone", "copy", "/home/danilo/Desktop/vpncud2.zip", "jjgdrive:", "-P"]
#
#     # Start the external command
#     process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#
#     # Read the output line by line in real time
#     while True:
#         output = process.stdout.readline()
#         if output == '' and process.poll() is not None:
#             break
#         if output:
#             # Print the matches
#             a, b = extract_rclone_progress(output)
#             if a:
#                 print(b)
#
#     # Get the return code of the process
#     return_code = process.poll()
#     print(f"Process finished with return code {return_code}")


class Processor(QObject):
    done = pyqtSignal(str)
    update = pyqtSignal(str)

    class Process:
        def __init__(self, command, name=None):
            self.process = None
            self.command = command
            self.done = False
            self.result = None
            self.running = False
            self.name = name

        def get_name(self):
            return self.name

        def poll(self):
            return self.process.poll() if self.process is not None else None

        def update(self):
            self.done = self.process is not None and self.process.poll() is not None
            self.running = self.process is not None and not self.done

    def __init__(self, max_threads=5):
        super().__init__()
        self.max_threads = max_threads
        self.running_threads = 0
        self.keep_running = True
        self.commands = []
        self.processes = []
        self.jobs = 0
        self.thread = None
        self.period = 0.25
        self.name = "jobs"

    def watcher(self):
        while self.keep_running:
            running = [p for p in self.processes if p.running]
            waiting = [p for p in self.processes if not p.running and not p.done]
            if len(running) < self.max_threads and len(waiting) > 0:
                waiting[0].process = subprocess.Popen(waiting[0].command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            for i, process in enumerate(self.processes):
                process.update()

            self.update.emit(self.name)

            if all([process.done for process in self.processes]):
                break

            print([p.command for p in self.processes if p.running])

            time.sleep(self.period)

        self.done.emit(self.name)

    def poll(self, index):
        return self.processes[index].stdout.readline()

    def poll_by_name(self, name):
        for i, process in enumerate(self.processes):
            if process.name == name:
                return process.stdout.readline()
        return None

    def count(self):
        return len(self.processes)

    def terminated(self):
        return all([process.done for process in self.processes])

    def get(self, index):
        return self.processes[index]

    def get_by_name(self, name):
        for process in self.processes:
            if process.name == name:
                return process
        return None

    def running(self):
        return [process for process in self.processes if process.running]

    def clear(self):
        self.commands.clear()
        self.processes.clear()

    def submit(self, command, name=None, clear=False):
        if clear:
            self.clear()
        name = "job#{}".format(len(self.commands)) if name is None else name
        self.processes.append(self.Process(command, name))

    def start(self, period=0.25, name="jobs"):
        self.period = period
        self.name = name
        self.keep_running = True
        self.jobs = len(self.commands)
        self.thread = threading.Thread(target=self.watcher).start()


if __name__ == "__main__":
    p = Processor(2)
    p.submit(["sleep", "1"])
    p.submit(["sleep", "2"])
    p.submit(["sleep", "3"])
    p.submit(["sleep", "4"])
    p.submit(["sleep", "5"])
    p.start()
    sleep(100)
    sys.exit(0)
    # real_time()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
