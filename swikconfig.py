import os
import gi

# gi.require_version('Gtk', '3.0')
# from gi.repository import Gtk, Gio, GLib

from PyQt5 import QtCore
from PyQt5.QtCore import QRect

from easyconfig.EasyConfig import EasyConfig


# from Dialogs import TextDontShowAgainDialog
# from gi.overrides.Gio import Gio
# from gi.overrides.Gtk import Gtk


class SwikConfig(EasyConfig):
    def __init__(self):
        super().__init__()
        self.base_dir = os.path.expanduser('~') + os.sep + '.swik' + os.sep
        self.set_dialog_minimum_size(500, 500)
        self.open_other_pdf_in = None
        self.init_config()

    def flush(self):
        self.save(self.base_dir + "swikV3.yaml")

    def get_open_other_pdf_in(self):
        return self.open_other_pdf_in.get_value()

    def init_config(self):

        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        if not os.path.exists(self.base_dir + os.sep + "script"):
            os.makedirs(self.base_dir + os.sep + "script")

        general = self.root().addSubSection("General")
        general.addString("file_browser", pretty="File Browser", default="/usr/bin/nautilus")
        general.addEditBox("other_pdf", pretty="Other PDF readers", height=50)
        general.addCheckbox("open_last", pretty="Reopen Last opened", default=True)
        general.addCheckbox("natural_hscroll", pretty="Natural H-Scroll")
        self.open_other_pdf_in = general.addCombobox("open_other_pdf_in", pretty="When opening other PDFs", items=["Same Window", "Other Window", "Ask"])
        self.flatten_before_sign = general.addCheckbox("flatten_before_sign", pretty="Flatten before signing", default=True)

        encryption = self.root().addSubSection("Encryption")
        encryption.addString("enc_suffix", pretty="Encrypted File Suffix", default="-enc")

        signature = self.root().addSubSection("Image Signature")
        signature.addFile("image_signature", pretty="Signature File", extension=["png", "jpg"], extension_name="Image")

        ## Private
        private = self.root().addSubSection("Private", hidden=True)
        private.addString("last")
        private.addList("recent")
        private.addInt("mode")
        private.addFloat("Ratio", default=1.5)
        private.addInt("Page", default=1)
        private.addInt("splitter1", default=235)
        private.addInt("splitter2", default=800)
        private.addInt("maximized", default=0)
        private.addInt("width", default=800)
        private.addInt("height", default=600)
        private.addInt("x")
        private.addInt("y")
        private.addInt("show_rename_dialog", default=True)
        private.addInt("show_signature_loss_dialog", default=True)
        private.addString("last_dir_for_open")
        private.addString("last_dir_for_rename")
        private.addString("last_dir_for_image")
        private.addDict("print_options")
        self.tabs = private.addList("tabs")

    def read(self):
        self.load(self.base_dir + "swikV3.yaml")

    def get_tabs(self, index=None):
        if index is not None:
            res = self.tabs.get_value()[index]
        else:
            res = self.tabs.get_value()
        return res if res is not None else []

    def set_tabs(self, tabs):
        self.tabs.set_value(tabs)

    def push_window_config(self, window):
        # self.set("Ratio", view.get_ratio())
        # self.set("mode", view.get_mode())
        self.set("maximized", 1 if window.windowState() & QtCore.Qt.WindowMaximized else 0)
        self.set("width", window.geometry().width())
        self.set("height", window.geometry().height())
        self.set("x", window.geometry().x())
        self.set("y", window.geometry().y())
        # self.update_recent(renderer.get_filename())

    def apply_window_config(self, window):
        if self.get("maximized"):
            window.setWindowState(QtCore.Qt.WindowMaximized)
        elif self.get("x") is not None:
            window.setGeometry(QRect(self.get("x"),
                                     self.get("y"),
                                     self.get("width"),
                                     self.get("height")))

    def update_recent(self, filename):
        recent = self.get("recent") if self.get("recent") is not None else []
        if filename in recent:
            recent.remove(filename)
        recent.insert(0, filename)
        recent = recent[0:10]
        self.set("recent", recent)

        # Add to Gtk Recent
        # rec_mgr = Gtk.RecentManager.get_default()
        # rec_mgr.add_item(Gio.File.new_for_path(filename).get_uri())
        # GLib.idle_add(Gtk.main_quit)
        # Gtk.main()

        return recent

    def fill_recent(self, window, open_recent):
        open_recent.clear()
        recent = self.get("recent")
        if recent is not None:
            for r in recent:
                open_recent.addAction(r, lambda x=r: window.open_file(x))

    def ask_once(self, key, text, parent=None):
        if self.get('/Private/' + key, True, True):
            ok, checked = TextDontShowAgainDialog("Info", text + "Continue?", parent).exec()
            if ok:
                self.set('/Private/' + key, not checked)
            return ok
        return True
