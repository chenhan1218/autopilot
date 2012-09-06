# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

import dbus

from PyQt4 import QtGui


def get_qt_icon():
    return QtGui.QIcon(":/trolltech/qmessagebox/images/qtlogo-64.png")

def dbus_string_rep(dbus_type):
    """Get a string representation of various dbus types."""
    if isinstance(dbus_type, dbus.Boolean):
        return repr(bool(dbus_type))
    if isinstance(dbus_type, dbus.String):
        return dbus_type.encode('ascii', errors='ignore')
    if (isinstance(dbus_type, dbus.Int16)
        or isinstance(dbus_type, dbus.UInt16)
        or isinstance(dbus_type, dbus.Int32)
        or isinstance(dbus_type, dbus.UInt32)
        or isinstance(dbus_type, dbus.Int64)
        or isinstance(dbus_type, dbus.UInt64)):
        return repr(int(dbus_type))
    if isinstance(dbus_type, dbus.Double):
        return repr(float(dbus_type))
    if (isinstance(dbus_type, dbus.Array)
        or isinstance(dbus_type, dbus.Struct)):
        return ', '.join([dbus_string_rep(i) for i in dbus_type])
    else:
        return repr(dbus_type)
