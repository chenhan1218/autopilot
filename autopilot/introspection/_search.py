# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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

"""Private Package for searching dbus for useful connections."""

from __future__ import absolute_import

from collections import namedtuple
import dbus
import logging
import os
import psutil

from autopilot.introspection.utilities import _get_bus_connections_pid


logger = logging.getLogger(__name__)


DbusConnection = namedtuple('DbusConnection', ['bus', 'connection_name'])


class FilterResult(object):
    PASS = object()
    FAIL = object()


class FilterRunner(object):

    def __init__(self, filter_list):
        if not filter_list:
            raise ValueError("Filter list must not be empty")
        self._filters = filter_list

    def matches(self, dbus_connection, search_parameters):
        for f in self._filters:
            result = f.matches(dbus_connection, search_parameters)
            if result == FilterResult.FAIL:
                return False
        return True


def FilterPrioritySorter(filter_list, runner_class):
    return runner_class(
        sorted(filter_list, cmp=lambda a, b: cmp(b.priority(), a.priority()))
    )


def FilterListGenerator(search_parameters, parameter_filter_lookup):
    filter_list = []
    search_param_copy = search_parameters.copy()
    try:
        for search_key in search_param_copy.keys():
            required_filter = parameter_filter_lookup[search_key]
            if required_filter not in filter_list:
                filter_list.append(required_filter)
            search_param_copy.pop(search_key)
    except KeyError:
        raise KeyError(
            "Search parameter %s doesn't have a corresponding filter in %r"
            % (search_key, parameter_filter_lookup),
        )

    return filter_list



# create filter list based on arguments
# create runner based on filter list

# def find_matching_connections():
#     connections = []

#     # Timer loop here
#     # populate connections based on the previous lot of connections
#     for c in connections:
#         if filter_runner(c, kwargs):
#            blah.append(c)
#     # valid_connections = [c for c in connections if filter_runner(c, kwargs)]
#     # if len(valid_connections) >= 1:
#     #     return valid_connections


# def _raise_if_process_exited(process):
#     """Raises ProcessSearchError if the non-None process is no longer running.

#     """
#     _get_child_pids.reset_cache()
#     if process is not None and not _process_is_running(process):
#         return_code = process.poll()
#         raise ProcessSearchError(
#             "Process exited with exit code: %d"
#             % return_code
#         )

class _cached_get_child_pids(object):
    """Get a list of all child process Ids, for the given parent.

    Since we call this often, and it's a very expensive call, we optimise this
    such that the return value will be cached for each scan through the dbus
    bus.

    Calling reset_cache() at the end of each dbus scan will ensure that you get
    fresh values on the next call.
    """

    def __init__(self):
        self._cached_result = None

    def __call__(self, pid):
        if self._cached_result is None:
            self._cached_result = [
                p.pid for p in psutil.Process(pid).get_children(recursive=True)
            ]
        return self._cached_result

    def reset_cache(self):
        self._cached_result = None


_get_child_pids = _cached_get_child_pids()


def _get_buses_unchecked_connection_names(dbus_bus, previous_connections=None):
    """Return a list of connections found on dbus_bus.

    If previous_connections is supplied then those connections are removed from
    the returned list.

    """
    def _get_unchecked_connections(all_conns):
        return list(set(all_conns).difference(set(previous_connections or [])))

    bus = _get_dbus_bus_from_string(dbus_bus)
    return _get_unchecked_connections(bus.list_name())

# Filters

# Need application name
class MatchesConnectionHasAppName(object):
    @classmethod
    def priority(cls):
        return 0  # LOW!

    @classmethod
    def matches(cls, dbus_connection, params):
        """Returns True if dbus_connection has the required application name.

        :raises KeyError if the 'application_name' parameter isn't passed in
            params

        """
        requested_app_name = params['application_name']
        bus, connection_name = dbus_connection

        dbus_object = cls._get_dbus_address_object(name, object_path, bus)
        app_name = cls._get_application_name_from_dbus_address(dbus_object)
        return app_name == requested_app_name

    @classmethod
    def _get_dbus_address_object(cls, connection_name, object_path, bus):
        return DBusAddress(bus, connection_name, object_path)

    @classmethod
    def _get_application_name_from_dbus_address(cls, dbus_address):
        """Return the application name from a dbus_address object."""
        return get_classname_from_path(
            dbus_address.introspection_iface.GetState('/')[0][0]
        )


# needs pid
class MatchesConnectionHasPid(object):

    @classmethod
    def priority(cls):
        return 0

    @classmethod
    def matches(cls, dbus_connection, params):
        """Match a connection based on the connections pid.

        :raises KeyError: if the pid parameter isn't passed in params.

        """
        pid = params['pid']
        bus, connection_name = dbus_connection

        if cls._should_ignore_pid(bus, connection_name, pid):
            return False

        try:
            bus_pid = _get_bus_connections_pid(bus, connection_name)
        except dbus.DBusException as e:
            logger.info(
                "dbus.DBusException while attempting to get PID for %s: %r" %
                (connection_name, e))
            return False

        eligible_pids = [pid] + _get_child_pids(pid)
        return bus_pid in eligible_pids

    @classmethod
    def _should_ignore_pid(cls, bus, connection_name, pid):
        if (
            connection_name == 'org.freedesktop.DBus'
            or _bus_pid_is_our_pid(bus, connection_name, pid)
        ):
            return True
        return False


def _bus_pid_is_our_pid(bus, connection_name, pid):
    """Returns True if this scripts pid is the bus connections pid supplied."""
    try:
        bus_pid = _get_bus_connections_pid(bus, connection_name)
        return bus_pid == os.getpid()
    except dbus.DBusException:
        return False


class MatchesConnectionHasPathWithAPInterface(object):

    @classmethod
    def priority(cls):
        return 0

    @classmethod
    def matches(cls, dbus_connection, params):
        """Ensure the connection has the path that we expect to be there.

        :raises ValueError: if the path parameter isn't included in params.

        """
        try:
            bus, connection_name = dbus_connection
            path = params['path']
            obj = bus.get_object(connection_name, path)
            dbus.Interface(
                obj,
                'com.canonical.Autopilot.Introspection'
            ).GetVersion()
            return True
        except KeyError:
            raise ValueError("Filter was expecting 'path' parameter")
        except dbus.DBusException:
            return False
