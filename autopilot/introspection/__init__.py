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


"""Package for introspection support.

This package contains the internal implementation of the autopilot
introspection mechanism, and probably isn't useful to most test authors.

"""

from __future__ import absolute_import

from autopilot.introspection._search import (
    get_autopilot_proxy_object_for_process,
    get_proxy_object_for_existing_process
)

from dbus import DBusException, Interface
import logging
from functools import partial
import os
import psutil
from six import u

from autopilot._timeout import Timeout
from autopilot.introspection.backends import DBusAddress


logger = logging.getLogger(__name__)

# Keep track of known connections during search
connection_list = []


def _maybe_filter_connections_by_app_name(application_name, dbus_addresses):
    """Filter `dbus_addresses` by the application name exported, if
    `application_name` has been specified.

    :returns: a filtered list of connections.
    """

    if application_name:
        dbus_addresses = [
            a for a in dbus_addresses
            if _get_application_name_from_dbus_address(a) == application_name
        ]
    return dbus_addresses


def _get_application_name_from_dbus_address(dbus_address):
    """Return the application name from a dbus_address object."""
    return get_classname_from_path(
        dbus_address.introspection_iface.GetState('/')[0][0]
    )




def _get_dbus_addresses_from_search_parameters(
        pid, dbus_bus, connection_name, object_path, process):
    """Returns a list of :py:class: `DBusAddress` for all successfully matched
    criteria.

    """
    _reset_known_connection_list()

    for _ in Timeout.default():
        _get_child_pids.reset_cache()
        if process is not None and not _process_is_running(process):
            return_code = process.poll()
            raise ProcessSearchError(
                "Process exited with exit code: %d"
                % return_code
            )

        bus = _get_dbus_bus_from_string(dbus_bus)

        valid_connections = _search_for_valid_connections(
            pid,
            bus,
            connection_name,
            object_path
        )

        if len(valid_connections) >= 1:
            return [_get_dbus_address_object(name, object_path, bus) for name
                    in valid_connections]
    return []


def _reset_known_connection_list():
    global connection_list
    del connection_list[:]


def _search_for_valid_connections(pid, bus, connection_name, object_path):
    global connection_list

    def _get_unchecked_connections(all_connections):
        return list(set(all_connections).difference(set(connection_list)))

    possible_connections = _get_possible_connections(bus, connection_name)
    connection_list = _get_unchecked_connections(possible_connections)
    valid_connections = _get_valid_connections(
        connection_list,
        bus,
        pid,
        object_path
    )

    return valid_connections


def _get_valid_connections(connections, bus, pid, object_path):
    filter_fn = partial(_match_connection, bus, pid, object_path)
    valid_connections = filter(filter_fn, connections)

    unique_connections = _dedupe_connections_on_pid(valid_connections, bus)

    return unique_connections


def _dedupe_connections_on_pid(valid_connections, bus):
    seen_pids = []
    deduped_connections = []

    for connection in valid_connections:
        pid = _get_bus_connections_pid(bus, connection)
        if pid not in seen_pids:
            seen_pids.append(pid)
            deduped_connections.append(connection)
    return deduped_connections





def _get_possible_connections(bus, connection_name):
    all_connection_names = bus.list_names()
    if connection_name is None:
        return all_connection_names
    else:
        matching_connections = [
            c for c in all_connection_names if c == connection_name]
        return matching_connections


def _match_connection(bus, pid, path, connection_name):
    """Does the connection match our search criteria?"""
    success = True
    if pid is not None:
        success = _connection_matches_pid(bus, connection_name, pid)
    if success:
        success = _connection_has_path(bus, connection_name, path)
    return success


def _connection_matches_pid(bus, connection_name, pid):
    """Given a PID checks wherever it or its children are connected on this
    bus.

    """
    if connection_name == 'org.freedesktop.DBus':
        return False
    try:
        if _bus_pid_is_our_pid(bus, connection_name, pid):
            return False
        bus_pid = _get_bus_connections_pid(bus, connection_name)
    except DBusException as e:
        logger.info(
            "dbus.DBusException while attempting to get PID for %s: %r" %
            (connection_name, e))
        return False
    eligible_pids = [pid] + _get_child_pids(pid)
    return bus_pid in eligible_pids


def _bus_pid_is_our_pid(bus, connection_name, pid):
    """Returns True if this scripts pid is the bus connections pid supplied."""
    bus_pid = _get_bus_connections_pid(bus, connection_name)
    return bus_pid == os.getpid()


def _connection_has_path(bus, connection_name, path):
    """Ensure the connection has the path that we expect to be there."""
    try:
        _check_connection_has_ap_interface(bus, connection_name, path)
        return True
    except DBusException:
        return False


def _check_connection_has_ap_interface(bus, connection_name, path):
    """Simple check if a bus with connection + path provide the Autopilot
    Introspection Interface.

    :raises: **DBusException** if it does not.

    """
    obj = bus.get_object(connection_name, path)
    obj_iface = Interface(obj, 'com.canonical.Autopilot.Introspection')
    obj_iface.GetVersion()
