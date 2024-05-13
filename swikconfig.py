import os
import gi

# gi.require_version('Gtk', '3.0')
# from gi.repository import Gtk, Gio, GLib

from PyQt5 import QtCore
from PyQt5.QtCore import QRect

# from Dialogs import TextDontShowAgainDialog
# from gi.overrides.Gio import Gio
# from gi.overrides.Gtk import Gtk
from easyconfig.EasyConfig import EasyConfig


class SwikConfig(EasyConfig):
    def __init__(self):
        super().__init__()
        self.base_dir = os.path.expanduser('~') + os.sep + '.swik' + os.sep
        self.set_dialog_minimum_size(500, 500)
        self.open_other_pdf_in = None

        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        if not os.path.exists(self.base_dir + os.sep + "script"):
            os.makedirs(self.base_dir + os.sep + "script")

        self.general = self.root().addSubSection("General")
        self.general.addString("file_browser", pretty="File Browser", default="/usr/bin/nautilus")
        self.general.addString("web_search", pretty="Web Search query", default="https://www.google.com/search?q=")
        self.general.addEditBox("other_pdf", pretty="Other PDF readers", height=50)
        self.general.addCheckbox("open_last", pretty="Reopen Last opened", default=True)
        self.general.addCombobox("lateral_bar_position", pretty="Lateral Bar Position", items=["Left", "Right", "Bottom", "Top"])
        self.general.addCheckbox("natural_hscroll", pretty="Natural H-Scroll")
        self.general.addCheckbox("fit_width_on_open", pretty="Fit Width on Open")

        self.open_other_pdf_in = self.general.addCombobox("open_other_pdf_in", pretty="When opening other PDFs", items=["Same Window", "Other Window", "Ask"])
        self.flatten_before_sign = self.general.addCheckbox("flatten_before_sign", pretty="Flatten before signing", default=True)

        encryption = self.root().addSubSection("Encryption")
        encryption.addString("enc_suffix", pretty="Encrypted File Suffix", default="-enc")

        # Private
        self.private = self.root().addSubSection("Private", hidden=True)
        self.private.addString("last")
        self.private.addList("recent")
        self.private.addInt("mode")
        self.private.addFloat("Ratio", default=1.5)
        self.private.addInt("Page", default=1)
        self.private.addInt("splitter1", default=235)
        self.private.addInt("splitter2", default=800)
        self.private.addInt("maximized", default=0)
        self.private.addInt("width", default=800)
        self.private.addInt("height", default=600)
        self.private.addInt("x")
        self.private.addInt("y")
        self.private.addInt("show_rename_dialog", default=True)
        self.private.addInt("show_signature_loss_dialog", default=True)
        self.private.addString("last_dir_for_open")
        self.private.addString("last_dir_for_rename")
        self.private.addString("last_dir_for_image")
        self.private.addDict("print_options")

        self.tabs = self.private.addDict("tabs")
        #self.zoom = self.private.addList("zoom")
        #self.pages = self.private.addList("pages")

    def flush(self):
        self.save(self.base_dir + "swikV3.yaml")

    def get_open_other_pdf_in(self):
        return self.open_other_pdf_in.get_value()

    def read(self):
        self.load(self.base_dir + "swikV3.yaml")

    def get_tabs(self, index=None):
        return self.tabs.get_value()

    def set_tabs(self, tabs):
        self.tabs.set_value(tabs)
        #self.zoom.set_value(zoom)
        #self.pages.set_value(page)

    def push_window_config(self, window):
        # self.set("Ratio", view.get_ratio())
        # self.set("mode", view.get_mode())
        self.private.set("maximized", 1 if window.windowState() & QtCore.Qt.WindowMaximized else 0)
        self.private.set("width", window.geometry().width())
        self.private.set("height", window.geometry().height())
        self.private.set("x", window.geometry().x())
        self.private.set("y", window.geometry().y())
        # self.update_recent(renderer.get_filename())

    def apply_window_config(self, window):
        if self.private.get("maximized"):
            window.setWindowState(QtCore.Qt.WindowMaximized)
        elif self.private.get("x") is not None:
            window.setGeometry(QRect(self.private.get("x"),
                                     self.private.get("y"),
                                     self.private.get("width"),
                                     self.private.get("height")))

    def update_recent(self, filename):
        recent = self.private.get("recent") if self.private.get("recent") is not None else []
        if filename in recent:
            recent.remove(filename)
        recent.insert(0, filename)
        recent = recent[0:10]
        self.private.set("recent", recent)

        # Add to Gtk Recent
        # rec_mgr = Gtk.RecentManager.get_default()
        # rec_mgr.add_item(Gio.File.new_for_path(filename).get_uri())
        # GLib.idle_add(Gtk.main_quit)
        # Gtk.main()

        return recent

    def fill_recent(self, window, open_recent):
        open_recent.clear()
        recent = self.private.get("recent")
        if recent is not None:
            for r in recent:
                open_recent.addAction(r, lambda x=r: window.open_file(x))

    def ask_once(self, key, text, parent=None):
        if self.private.get('/Private/' + key, True, True):
            ok, checked = TextDontShowAgainDialog("Info", text + "Continue?", parent).exec()
            if ok:
                self.private.set('/Private/' + key, not checked)
            return ok
        return True
