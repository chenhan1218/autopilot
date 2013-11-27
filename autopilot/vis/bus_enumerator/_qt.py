
from collections import defaultdict

from autopilot.vis.bus_enumerator._functional import start_trawl

from PyQt4.QtCore import (
    pyqtSignal,
    QObject,
)


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

    def get_found_connections(self):
        """Get a list of found connection names. This may not be up to date."""
        return list(self._data.keys())

    def get_found_objects(self, connection_string):
        """Get a list of found objects for a particular connection name.

        This may be out of date.

        """
        if connection_string not in self._data:
            raise KeyError("%s not in results" % connection_string)
        return list(self._data[connection_string].keys())

    def get_found_interfaces(self, connection_string, object_path):
        """Get a list of found interfaces for a particular connection name and
        object path.

        This may be out of date.

        """
        if connection_string not in self._data:
            raise KeyError("connection %s not in results" % connection_string)
        if object_path not in self._data[connection_string]:
            raise KeyError(
                "object %s not in results for connection %s" %
                (object_path, connection_string))
        return self._data[connection_string][object_path]

    def start_trawl(self):
        """Start trawling the bus for interfaces."""
        for connection in self._bus.list_names():
            _start_trawl(self._bus, connection, self._add_hit)

    def _add_hit(self, conn_name, obj_name, interface_name):
        self.new_interface_found.emit(conn_name, obj_name, interface_name)
        self._data[conn_name][obj_name].append(interface_name)
