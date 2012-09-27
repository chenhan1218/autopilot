# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
from collections import defaultdict

from os.path import join
from PyQt4.QtCore import (
    pyqtSignal,
    qDebug,
    QObject,
    )
from xml.etree import ElementTree


class BusEnumerator(QObject):
    """A simple utility class to support enumeration of all DBus connections,
    objects, and interfaces.

    Create an instance of ths class, and connect to the new_interface_found
    signal.

    """

    new_interface_found = pyqtSignal(str, str, str)

    def __init__(self, bus):
        super(BusEnumerator, self).__init__()
        self._bus = bus
        self._data = defaultdict(lambda: defaultdict(list))

    def start_trawl(self):
        """Start trawling the bus for interfaces."""
        for connection in self._bus.list_names():
            self._get_objects_and_interfaces(connection)

    def _get_objects_and_interfaces(self, conn_name, obj_name='/'):
        """Return a list of objects and their interfaces.

        """
        obj = self._bus.get_object(conn_name, obj_name)
        obj.Introspect(dbus_interface='org.freedesktop.DBus.Introspectable',
            reply_handler=lambda xml: self._reply_handler(conn_name, obj_name, xml),
            error_handler=self._error_handler)

    def _error_handler(self, *error):
        qDebug("Error is: %r" % error)

    def _reply_handler(self, conn_name, obj_name, xml):
        root = ElementTree.fromstring(xml)

        for child in root.getchildren():
            child_name = join(obj_name, child.attrib['name'])
            if child.tag == 'node':
                self._get_objects_and_interfaces(
                                                conn_name,
                                                child_name)
            elif child.tag == 'interface':
                iface_name = child_name.split('/')[-1]
                self._add_hit(conn_name, obj_name, iface_name)

    def _add_hit(self, conn_name, obj_name, interface_name):
        self.new_interface_found.emit(conn_name, obj_name, interface_name)
        self._data[conn_name][obj_name].append(interface_name)

    def get_found_connections(self):
        """Get a list of found connection names. This may not be up to date."""
        return self._data.keys()

    def get_found_objects(self, connection_string):
        """Get a list of found objects for a particular connection name.

        This may be out of date.

        """
        if connection_string not in self._data.keys():
            raise KeyError("%s not in results" % connection_string)
        return self._data[connection_string].keys()

    def get_found_interfaces(self, connection_string, object_path):
        """Get a list of found interfaces for a particular connection name and
        object path.

        This may be out of date.

        """
        if connection_string not in self._data.keys():
            raise KeyError("connection %s not in results" % connection_string)
        if object_path not in self._data[connection_string].keys():
            raise KeyError("object %s not in results for connection %s" % (object_path, connection_string))
        return self._data[connection_string][object_path]


