# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import dbus
from dbus.mainloop.qt import DBusQtMainLoop
from PyQt4 import QtGui
import sys

from autopilot.vis.bus_enumerator import BusEnumerator
from autopilot.vis.main_window import MainWindow

def vis_main():
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName("Autopilot")
    app.setOrganizationName("Canonical")

    dbus_loop = DBusQtMainLoop()
    session_bus = dbus.SessionBus(mainloop=dbus_loop)

    window = MainWindow()

    bus_enumerator = BusEnumerator(session_bus)
    bus_enumerator.new_interface_found.connect(window.on_interface_found)
    bus_enumerator.start_trawl()

    window.show()
    sys.exit(app.exec_())

