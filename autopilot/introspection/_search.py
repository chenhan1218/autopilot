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

import dbus
import logging
import os
import psutil
import subprocess
from functools import partial
from operator import methodcaller
from six import u

from autopilot._timeout import Timeout
from autopilot.dbus_handler import (
    get_session_bus,
    get_system_bus,
    get_custom_bus,
)
from autopilot.exceptions import ProcessSearchError
from autopilot.introspection.backends import DBusAddress

from autopilot.introspection.constants import (
    AUTOPILOT_PATH,
    QT_AUTOPILOT_IFACE,
    AP_INTROSPECTION_IFACE,
)
from autopilot.introspection.dbus import (
    CustomEmulatorBase,
    DBusIntrospectionObject,
    get_classname_from_path,
)
from autopilot.introspection.utilities import (
    _get_bus_connections_pid,
    _pid_is_running,
)


logger = logging.getLogger(__name__)


class FilterResult(object):
    PASS = object()
    FAIL = object()


def matches(filter_list, dbus_connection, search_parameters):
    if not filter_list:
        raise ValueError("Filter list must not be empty")
    for f in filter_list:
        result = f.matches(dbus_connection, search_parameters)
        if result == FilterResult.FAIL:
            return False
    return True


def _filter_function_from_search_params(search_parameters, filter_lookup=None):
    """Returns a callable filter function that will use a prioritised filter
    list based on the search_parameters.

    """

    parameter_filter_lookup = filter_lookup or _param_to_filter_map
    filter_list = []
    try:
        for search_key in search_parameters.keys():
            required_filter = parameter_filter_lookup[search_key]
            if required_filter not in filter_list:
                filter_list.append(required_filter)
    except KeyError:
        raise KeyError(
            "Search parameter %s doesn't have a corresponding filter in %r"
            % (search_key, parameter_filter_lookup),
        )

    sorted_filter_list = sorted(
        filter_list,
        key=methodcaller('priority'),
        reverse=True
    )
    return partial(matches, sorted_filter_list)


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


class MatchesConnectionHasAppName(object):
    @classmethod
    def priority(cls):
        return 0  # LOW

    @classmethod
    def matches(cls, dbus_connection, params):
        """Returns True if dbus_connection has the required application name.

        Can be provided an object_path but defaults to 'AUTOPILOT_PATH' if not
        provided.

        This filter should only activated if the application_name is provided
        in the search criteria.

        :raises KeyError if the 'application_name' parameter isn't passed in
            params

        """
        requested_app_name = params['application_name']
        object_path = params.get('object_path', AUTOPILOT_PATH)
        bus, connection_name = dbus_connection

        dbus_object = _get_dbus_address_object(
            connection_name,
            object_path,
            bus
        )
        app_name = cls._get_application_name_from_dbus_address(dbus_object)
        return app_name == requested_app_name

    @classmethod
    def _get_application_name_from_dbus_address(cls, dbus_address):
        """Return the application name from a dbus_address object."""
        return get_classname_from_path(
            dbus_address.introspection_iface.GetState('/')[0][0]
        )


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
            or cls._bus_pid_is_our_pid(bus, connection_name, pid)
        ):
            return True
        return False

    @classmethod
    def _bus_pid_is_our_pid(cls, bus, connection_name, pid):
        """Returns True if this processes pid is the same as the supplied bus
        connections pid.

        """
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


_param_to_filter_map = dict(
    application_name=MatchesConnectionHasAppName,
    pid=MatchesConnectionHasPid,
    path=MatchesConnectionHasPathWithAPInterface,
)


def get_autopilot_proxy_object_for_process(
    process,
    emulator_base,
    dbus_bus='session'
):
    """Return the autopilot proxy object for the given *process*.

    :raises: **RuntimeError** if no autopilot interface was found.

    """
    pid = process.pid
    proxy_obj = get_proxy_object_for_existing_process(
        pid,
        process=process,
        emulator_base=emulator_base,
        dbus_bus=dbus_bus,
    )
    proxy_obj.set_process(process)

    return proxy_obj


def get_proxy_object_for_existing_process(**kwargs):
        # pid=None, dbus_bus='session', connection_name=None, process=None,
        # object_path=AUTOPILOT_PATH, application_name=None,
        # emulator_base=None):
    """Return a single proxy object for an application that is already running
    (i.e. launched outside of Autopilot).

    Searches on the given bus (supplied by **dbus_bus**) for an application
    matching the search criteria, creating the proxy object using the supplied
    custom emulator **emulator_base** (defaults to None).

    For example for an application on the system bus where the applications
    PID is known::

        app_proxy = get_proxy_object_for_existing_process(pid=app_pid)

    Multiple criteria are allowed, for instance you could search on **pid**
    and **connection_name**::

        app_proxy = get_proxy_object_for_existing_process(
            pid=app_pid, connection_name='org.gnome.gedit')

    If the application from the previous example was on the system bus::

        app_proxy = get_proxy_object_for_existing_process(
            dbus_bus='system', pid=app_pid, connection_name='org.gnome.gedit')

    It is possible to search for the application given just the applications
    name.
    An example for an application running on a custom bus searching using the
    applications name::

        app_proxy = get_proxy_object_for_existing_process(
            application_name='qmlscene',
            dbus_bus='unix:abstract=/tmp/dbus-IgothuMHNk')

    :param pid: The PID of the application to search for.
    :param dbus_bus: A string containing either 'session', 'system' or the
        custom buses name (i.e. 'unix:abstract=/tmp/dbus-IgothuMHNk').
    :param connection_name: A string containing the DBus connection name to
        use with the search criteria.
    :param object_path: A string containing the object path to use as the
        search criteria. Defaults to
        :py:data:`autopilot.introspection.constants.AUTOPILOT_PATH`.
    :param application_name: A string containing the applications name to
        search for.
    :param emulator_base: The custom emulator to create the resulting proxy
        object with.

    :raises ProcessSearchError: if no search criteria match.
    :raises RuntimeError: if the search criteria results in many matches.
    :raises RuntimeError: if both ``process`` and ``pid`` are supplied, but
        ``process.pid != pid``.

    """
    # Pop off non-search stuff.
    dbus_bus = kwargs.pop('dbus_bus', 'session')
    process = kwargs.pop('process', None)
    emulator_base = kwargs.pop('emulator_base', None)

    # pid=None
    # connection_name=None,
    # object_path=AUTOPILOT_PATH
    # application_name=None

    # Special handling of pid.
    pid = _check_process_and_pid_details(process, kwargs.get('pid', None))
    kwargs['pid'] = kwargs.get('pid', pid or None)

    matcher_function = _filter_function_from_search_params(kwargs)

    # Perhaps move the arguments of matcher_function so we can use another
    # partial here?
    connections = _find_matching_connections(
        dbus_bus,
        lambda connection: matcher_function(connection, kwargs),
        process
    )

    _raise_if_unusable_amount_of_results(
        connections,
        _get_search_criteria_string_representation(**kwargs)
    )

    object_path = kwargs.get('object_path', AUTOPILOT_PATH)
    connection_name = connections[0][1]
    return _make_proxy_object(
        _get_dbus_address_object(connection_name, object_path, dbus_bus),
        emulator_base
    )


def _check_process_and_pid_details(process=None, pid=None):
    """Do error checking on process and pid specification.

    :raises RuntimeError: if both process and pid are specified, but the
        process's 'pid' attribute is different to the pid attribute specified.
    :raises ProcessSearchError: if the process specified is not running.
    :returns: the pid to use in all search queries.

    """
    if process is not None:
        if pid is None:
            pid = process.pid
        elif pid != process.pid:
            raise RuntimeError("Supplied PID and process.pid do not match.")

    if pid is not None and not _pid_is_running(pid):
        raise ProcessSearchError("PID %d could not be found" % pid)
    return pid


def _raise_if_unusable_amount_of_results(connections, criteria_string):
    if connections is None or len(connections) == 0:
        raise ProcessSearchError(
            "Search criteria (%s) returned no results" %
            (criteria_string)
        )

    if len(connections) > 1:
        raise RuntimeError(
            "Search criteria (%s) returned multiple results"
            % (criteria_string)
        )


def _find_matching_connections(dbus_bus, connection_matcher, process=None):
    """Returns a list of connection names that have passed the
    connection_matcher.

    :param dbus_bus: String naming which dbus bus to search
    :param connection_matcher: Callable that takes a connection name and
        returns True if it is what we're looking for.
    :param process: A process object that we're looking for it's dbus
        connection. Used to ensure that the process is in fact still running
        while we're searching for it.

    """
    connections = []

    bus = _get_dbus_bus_from_string(dbus_bus)

    for _ in Timeout.default():
        _raise_if_process_has_exited(process)

        connections = [
            (bus, connection)
            for connection
            in _get_buses_unchecked_connection_names(bus, connections)
        ]

        # Grab out only the connection names
        valid_connections = [
            c[1] for c
            in connections
            if connection_matcher(c)
        ]


        # If nothing was found go round for another go.
        if len(valid_connections) >= 1:
            return _dedupe_connections_on_pid(valid_connections, bus)

    return []


def _dedupe_connections_on_pid(valid_connections, bus):
    seen_pids = []
    deduped_connections = []

    for connection in valid_connections:
        pid = _get_bus_connections_pid(bus, connection)
        if pid not in seen_pids:
            seen_pids.append(pid)
            deduped_connections.append(connection)
    return deduped_connections


def _get_dbus_bus_from_string(dbus_string):
    if dbus_string == 'session':
        return get_session_bus()
    elif dbus_string == 'system':
        return get_system_bus()
    else:
        return get_custom_bus(dbus_string)


def _raise_if_process_has_exited(process):
    """Raises ProcessSearchError if process is no longer running."""
    _get_child_pids.reset_cache()
    if process is not None and not _process_is_running(process):
        return_code = process.poll()
        raise ProcessSearchError(
            "Process exited with exit code: %d"
            % return_code
        )


def _process_is_running(process):
    return process.poll() is None


def _get_buses_unchecked_connection_names(dbus_bus, previous_connections=None):
    """Return a list of connections found on dbus_bus.

    If previous_connections is supplied then those connections are removed from
    the returned list.

    """
    all_conns = dbus_bus.list_names()
    return list(set(all_conns).difference(set(previous_connections or [])))


def _make_proxy_object(data_source, emulator_base):
    """Returns a root proxy object given a DBus service name."""
    proxy_bases = _get_proxy_object_base_classes(data_source)
    if emulator_base is None:
        emulator_base = type('DefaultEmulatorBase', (CustomEmulatorBase,), {})
    proxy_bases = proxy_bases + (emulator_base, )
    cls_name, cls_state = _get_proxy_object_class_name_and_state(data_source)

    # Merge the object hierarchy.
    clsobj = type(str("%sBase" % cls_name), proxy_bases, {})

    proxy_class = type(str(cls_name), (clsobj,), {})

    try:
        dbus_tuple = data_source.introspection_iface.GetState("/")[0]
        path, state = dbus_tuple
        return proxy_class(state, path, data_source)
    except IndexError:
        raise RuntimeError("Unable to find root object of %r" % proxy_class)


def _get_proxy_object_class_name_and_state(backend):
    """Return the class name and root state dictionary."""
    object_path, object_state = backend.introspection_iface.GetState("/")[0]
    return get_classname_from_path(object_path), object_state


def _get_proxy_object_base_classes(backend):
    """Return  tuple of the base classes to use when creating a proxy object
    for the given service name & path.

    :raises: **RuntimeError** if the autopilot interface cannot be found.

    """

    bases = [ApplicationProxyObject]

    intro_xml = backend.dbus_introspection_iface.Introspect()
    if AP_INTROSPECTION_IFACE not in intro_xml:
        raise RuntimeError(
            "Could not find Autopilot interface on DBus backend '%s'" %
            backend)

    if QT_AUTOPILOT_IFACE in intro_xml:
        from autopilot.introspection.qt import QtObjectProxyMixin
        bases.append(QtObjectProxyMixin)

    return tuple(bases)


def _get_dbus_address_object(connection_name, object_path, bus):
    return DBusAddress(bus, connection_name, object_path)


def _get_search_criteria_string_representation(**kwargs):
    return ", ".join([
        u("%s = %r") % (k.replace("_", " "), v)
        for k, v
        in kwargs.iteritems()
    ])


class ApplicationProxyObject(DBusIntrospectionObject):
    """A class that better supports query data from an application."""

    def __init__(self, state, path, backend):
        super(ApplicationProxyObject, self).__init__(state, path, backend)
        self._process = None

    def set_process(self, process):
        """Set the subprocess.Popen object of the process that this is a proxy
        for.

        You should never normally need to call this method.

        """
        self._process = process

    @property
    def pid(self):
        return self._process.pid

    @property
    def process(self):
        return self._process

    def kill_application(self):
        """Kill the running process that this is a proxy for using
        'kill `pid`'."""
        subprocess.call(["kill", "%d" % self._process.pid])
