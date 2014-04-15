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

from collections import namedtuple
import dbus
import logging

from autopilot.dbus_handler import (
    get_session_bus,
    get_system_bus,
    get_custom_bus,
)
from autopilot.introspection.constants import (
    AP_INTROSPECTION_IFACE,
    CURRENT_WIRE_PROTOCOL_VERSION,
    DBUS_INTROSPECTION_IFACE,
    QT_AUTOPILOT_IFACE,
)
from autopilot.utilities import Timer
from autopilot.introspection.utilities import (
    _pid_is_running,
    _get_bus_connections_pid,
)


_logger = logging.getLogger(__name__)


class WireProtocolVersionMismatch(RuntimeError):
    """Wire protocols mismatch."""


class DBusAddress(object):
    """Store information about an Autopilot dbus backend, from keyword
    arguments."""
    _checked_backends = []

    AddrTuple = namedtuple(
        'AddressTuple', ['bus', 'connection', 'object_path'])

    @staticmethod
    def SessionBus(connection, object_path):
        """Construct a DBusAddress that backs on to the session bus."""
        return DBusAddress(get_session_bus(), connection, object_path)

    @staticmethod
    def SystemBus(connection, object_path):
        """Construct a DBusAddress that backs on to the system bus."""
        return DBusAddress(get_system_bus(), connection, object_path)

    @staticmethod
    def CustomBus(bus_address, connection, object_path):
        """Construct a DBusAddress that backs on to a custom bus.

        :param bus_address: A string representing the address of the dbus bus
            to connect to.

        """
        return DBusAddress(
            get_custom_bus(bus_address), connection, object_path)

    def __init__(self, bus, connection, object_path):
        """Construct a DBusAddress instance.

        :param bus: A valid DBus bus object.
        :param connection: A string connection name to look at, or None to
            search all dbus connections for objects that resemble an autopilot
            conection.
        :param object_path: The path to the object that provides the autopilot
            interface, or None to search for the object.

        """
        # We cannot evaluate kwargs for accuracy now, since this class will be
        # created at module import time, at which point the bus backend
        # probably does not exist yet.
        self._addr_tuple = DBusAddress.AddrTuple(bus, connection, object_path)

    @property
    def introspection_iface(self):
        if not isinstance(self._addr_tuple.connection, str):
            raise TypeError("Service name must be a string.")
        if not isinstance(self._addr_tuple.object_path, str):
            raise TypeError("Object name must be a string")

        if not self._check_pid_running():
            raise RuntimeError(
                "Application under test exited before the test finished!"
            )

        proxy_obj = self._addr_tuple.bus.get_object(
            self._addr_tuple.connection,
            self._addr_tuple.object_path
        )
        iface = dbus.Interface(proxy_obj, AP_INTROSPECTION_IFACE)
        if self._addr_tuple not in DBusAddress._checked_backends:
            try:
                self._check_version(iface)
            except WireProtocolVersionMismatch:
                raise
            else:
                DBusAddress._checked_backends.append(self._addr_tuple)
        return iface

    def _check_version(self, iface):
        """Check the wire protocol version on 'iface', and raise an error if
        the version does not match what we were expecting.

        """
        try:
            version = iface.GetVersion()
        except dbus.DBusException:
            version = "1.2"
        if version != CURRENT_WIRE_PROTOCOL_VERSION:
            raise WireProtocolVersionMismatch(
                "Wire protocol mismatch at %r: is %s, expecting %s" % (
                    self,
                    version,
                    CURRENT_WIRE_PROTOCOL_VERSION)
            )

    def _check_pid_running(self):
        try:
            process_pid = _get_bus_connections_pid(
                self._addr_tuple.bus,
                self._addr_tuple.connection
            )
            return _pid_is_running(process_pid)
        except dbus.DBusException as e:
            if e.get_dbus_name() == \
                    'org.freedesktop.DBus.Error.NameHasNoOwner':
                return False
            else:
                raise

    @property
    def dbus_introspection_iface(self):
        dbus_object = self._addr_tuple.bus.get_object(
            self._addr_tuple.connection,
            self._addr_tuple.object_path
        )
        return dbus.Interface(dbus_object, DBUS_INTROSPECTION_IFACE)

    @property
    def qt_introspection_iface(self):
        proxy_obj = self._addr_tuple.bus.get_object(
            self._addr_tuple.connection,
            self._addr_tuple.object_path
        )
        return dbus.Interface(proxy_obj, QT_AUTOPILOT_IFACE)

    def __hash__(self):
        return hash(self._addr_tuple)

    def __eq__(self, other):
        return self._addr_tuple.bus == other._addr_tuple.bus and \
            self._addr_tuple.connection == other._addr_tuple.connection and \
            self._addr_tuple.object_path == other._addr_tuple.object_path

    def __ne__(self, other):
        return (self._addr_tuple.object_path !=
                other._addr_tuple.object_path or
                self._addr_tuple.connection != other._addr_tuple.connection or
                self._addr_tuple.bus != other._addr_tuple.bus)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        if self._addr_tuple.bus._bus_type == dbus.Bus.TYPE_SESSION:
            name = "session"
        elif self._addr_tuple.bus._bus_type == dbus.Bus.TYPE_SYSTEM:
            name = "system"
        else:
            name = "custom"
        return "<%s bus %s %s>" % (
            name, self._addr_tuple.connection, self._addr_tuple.object_path)


def execute_query(query, backend):
    """Execute 'query' on 'backend', returning new proxy objects."""
    with Timer("GetState %r" % query):
        data = backend.introspection_iface.GetState(query.server_query_bytes())
        if len(data) > 15:
            _logger.warning(
                "Your query '%r' returned a lot of data (%d items). This "
                "is likely to be slow. You may want to consider optimising"
                " your query to return fewer items.",
                query,
                len(data)
            )

