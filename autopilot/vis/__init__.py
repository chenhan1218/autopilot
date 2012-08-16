import sys
import dbus
from dbus.mainloop.qt import DBusQtMainLoop
from autopilot.vis.bus_enumerator import BusEnumerator
from autopilot.vis.main_window import MainWindow
from PyQt4 import QtGui

def vis_main():
    app = QtGui.QApplication(sys.argv)

    dbus_loop = DBusQtMainLoop()
    session_bus = dbus.SessionBus(mainloop=dbus_loop)

    window = MainWindow()

    bus_enumerator = BusEnumerator(session_bus)
    bus_enumerator.new_interface_found.connect(window.on_interface_found)
    bus_enumerator.start_trawl()

    window.show()
    sys.exit(app.exec_())
