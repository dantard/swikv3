import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

from PyQt5.QtCore import pyqtSignal, QThread


class SwikDBusService(dbus.service.Object):
    def __init__(self, bus_name, object_path, callback):
        self.callback = callback
        dbus.service.Object.__init__(self, bus_name, object_path)

    @dbus.service.method("com.swik.server_interface", in_signature='s', out_signature='s')
    def open(self, filename):
        self.callback(filename)
        return "OK"

class DBusServerThread(QThread):

    open_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def callback(self, filename):
        self.open_requested.emit(filename)

    def run(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        bus = dbus.SessionBus()
        name = dbus.service.BusName("com.swik.server", bus)
        object_path = "/com/swik/server"
        service = SwikDBusService(name, object_path, self.callback)
        loop = GLib.MainLoop()
        loop.run()