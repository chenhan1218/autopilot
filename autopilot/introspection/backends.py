# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"Backend interface for autopilot."
from __future__ import absolute_import

from autopilot.dbus_handler import (
    get_session_bus,
    get_system_bus,
    get_custom_bus,
    )

import dbus

from autopilot.introspection.constants import (
    AP_INTROSPECTION_IFACE,
    DBUS_INTROSPECTION_IFACE,
    QT_AUTOPILOT_IFACE,
    )


class DBusAddress(object):

    "Store information about an Autopilot dbus backend, from keyword arguments."

    @staticmethod
    def SessionBus(connection, object_path):
        """Construct a DBusAddress that backs on to the session bus."""
        return DBusAddress(get_session_bus(), connection, object_path)

    @staticmethod
    def SystemBus(connection, object_path):
        """Construct a DBusAddress that backs on to the system bus."""
        return DBusAddress(dbus.SystemBus(), connection, object_path)

    @staticmethod
    def CustomBus(bus_address, connection, object_path):
        """Construct a DBusAddress that backs on to a custom bus.

        :param bus_address: A string representing the address of the dbus bus to
            connect to.

        """
        return DBusAddress(get_custom_bus(bus_address), connection, object_path)

    def __init__(self, bus, connection, object_path):
        """Construct a DBusAddress instance.

        :param bus: A valid DBus bus object.
        :param connection: A string connection name to look at, or None to search
            all dbus connections for objects that resemble an autopilot conection.
        :param object_path: The path to the object that provides the autopilot
            interface, or None to search for the object.

        """
        # We cannot evaluate kwargs for accuracy now, since this class will be
        # created at module import time, at which point the bus backend probably
        # does not exist yet.
        self._bus = bus
        self._connection = connection
        self._object_path = object_path

    @property
    def introspection_iface(self):
        if not isinstance(self._connection, basestring):
            raise TypeError("Service name must be a string.")
        if not isinstance(self._object_path, basestring):
            raise TypeError("Object name must be a string")

        _debug_proxy_obj = self._bus.get_object(self._connection, self._object_path)
        return dbus.Interface(_debug_proxy_obj, AP_INTROSPECTION_IFACE)

    @property
    def dbus_introspection_iface(self):
        dbus_object = self._bus.get_object(self._connection, self._object_path)
        return dbus.Interface(dbus_object, DBUS_INTROSPECTION_IFACE)

    @property
    def qt_introspection_iface(self):
        _debug_proxy_obj = self._bus.get_object(self._connection, self._object_path)
        return dbus.Interface(_debug_proxy_obj, QT_AUTOPILOT_IFACE)

    def __hash__(self):
        return hash((self._bus, self._connection, self._object_path))

    def __eq__(self, other):
        return self._bus == other._bus and \
            self._connection == other._connection and \
            self._object_path == other._object_path

    def __ne__(self, other):
        return self._object_path != other._object_path or \
            self._connection != other._connection or \
            self._bus != other._bus

    def __str__(self):
        return repr(self)

    def __repr__(self):
        if self._bus._bus_type == dbus.Bus.TYPE_SESSION:
            name = "session"
        elif self._bus._bus_type == dbus.Bus.TYPE_SYSTEM:
            name = "system"
        else:
            name = "custom"
        return "<%s bus %s %s>" % (name, self._connection, self._object_path)

