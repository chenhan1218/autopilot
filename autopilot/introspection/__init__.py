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

from dbus import DBusException, Interface
import logging
import subprocess
from functools import partial
import os
import psutil
from six import u

from autopilot.dbus_handler import (
    get_session_bus,
    get_system_bus,
    get_custom_bus,
)
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
from autopilot._timeout import Timeout


logger = logging.getLogger(__name__)

# Keep track of known connections during search
connection_list = []


class ProcessSearchError(RuntimeError):
    pass


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


def get_proxy_object_for_existing_process(
        pid=None, dbus_bus='session', connection_name=None, process=None,
        object_path=AUTOPILOT_PATH, application_name=None, emulator_base=None):
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
    pid = _check_process_and_pid_details(process, pid)

    dbus_addresses = _get_dbus_addresses_from_search_parameters(
        pid,
        dbus_bus,
        connection_name,
        object_path,
        process
    )

    dbus_addresses = _maybe_filter_connections_by_app_name(
        application_name,
        dbus_addresses
    )

    if dbus_addresses is None or len(dbus_addresses) == 0:
        criteria_string = _get_search_criteria_string_representation(
            pid,
            dbus_bus,
            connection_name,
            process,
            object_path,
            application_name
        )
        message_string = "Search criteria (%s) returned no results" % \
            (criteria_string)
        raise ProcessSearchError(message_string)
    if len(dbus_addresses) > 1:
        criteria_string = _get_search_criteria_string_representation(
            pid,
            dbus_bus,
            connection_name,
            process,
            object_path,
            application_name
        )
        message_string = "Search criteria (%s) returned multiple results" % \
            (criteria_string)
        raise RuntimeError(message_string)

    return _make_proxy_object(dbus_addresses[0], emulator_base)


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


def _get_search_criteria_string_representation(
        pid=None, dbus_bus=None, connection_name=None, process=None,
        object_path=None, application_name=None):
    """Get a string representation of the search criteria.

    Used to represent the search criteria to users in error messages.
    """
    description_parts = []
    if pid is not None:
        description_parts.append(u('pid = %d') % pid)
    if dbus_bus is not None:
        description_parts.append(u("dbus bus = '%s'") % dbus_bus)
    if connection_name is not None:
        description_parts.append(
            u("connection name = '%s'") % connection_name
        )
    if object_path is not None:
        description_parts.append(u("object path = '%s'") % object_path)
    if application_name is not None:
        description_parts.append(
            u("application name = '%s'") % application_name
        )
    if process is not None:
        description_parts.append(u("process object = '%r'") % process)

    return ", ".join(description_parts)


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


def _process_is_running(process):
    return process.poll() is None


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


def _get_dbus_address_object(connection_name, object_path, bus):
    return DBusAddress(bus, connection_name, object_path)


def _get_dbus_bus_from_string(dbus_string):
    if dbus_string == 'session':
        return get_session_bus()
    elif dbus_string == 'system':
        return get_system_bus()
    else:
        return get_custom_bus(dbus_string)


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


def _make_proxy_object(data_source, emulator_base):
    """Returns a root proxy object given a DBus service name.

    :param data_source: The dbus backend address object we're querying.
    :param emulator_base: The emulator base object (or None), as provided by
        the user.
    """
    intro_xml = _get_introspection_xml_from_backend(data_source)
    cls_name, path, cls_state = _get_proxy_object_class_name_and_state(
        data_source
    )

    try:
        proxy_bases = _get_proxy_bases_from_introspection_xml(intro_xml)
    except RuntimeError as e:
        e.args = (
            "Could not find Autopilot interface on dbus address '%s'."
            % data_source,
        )
        raise e
    proxy_bases = _extend_proxy_bases_with_emulator_base(
        proxy_bases,
        emulator_base
    )
    proxy_class = _make_proxy_class_object(cls_name, proxy_bases)

    return proxy_class(cls_state, path, data_source)


def _make_proxy_object_async(
        data_source, emulator_base, reply_handler, error_handler):
    """Make a proxy object for a dbus backend.

    Similar to :meth:`_make_proxy_object` except this method runs
    asynchronously and must have a reply_handler callable set. The
    reply_handler will be called with a single argument: The proxy object.

    """
    # Note: read this function backwards!
    #
    # Due to the callbacks, I need to define the end of the callback chain
    # first, so start reading from the bottom of the function upwards, and
    # it'll make a whole lot more sense.

    # Final phase: We have all the information we need, now we construct
    # everything. This phase has no dbus calls, and so is very fast:
    def build_proxy(introspection_xml, cls_name, path, cls_state):
        proxy_bases = _get_proxy_bases_from_introspection_xml(
            introspection_xml
        )
        proxy_bases = _extend_proxy_bases_with_emulator_base(
            proxy_bases,
            emulator_base
        )
        proxy_class = _make_proxy_class_object(cls_name, proxy_bases)
        reply_handler(proxy_class(cls_state, path, data_source))

    # Phase 2: We recieve the introspection string, and make an asynchronous
    # dbus call to get the state information for the root of this applicaiton.
    def get_root_state(introspection_xml):
        _get_proxy_object_class_name_and_state(
            data_source,
            reply_handler=partial(build_proxy, introspection_xml),
            error_handler=error_handler,
        )

    # Phase 1: Make an asynchronous dbus call to get the introspection xml
    # from the data_source provided for us.
    _get_introspection_xml_from_backend(
        data_source,
        reply_handler=get_root_state,
        error_handler=error_handler
    )


def _get_introspection_xml_from_backend(
        backend, reply_handler=None, error_handler=None):
    """Get DBus Introspection xml from a backend.

    :param backend: The backend object to query.
    :param reply_handler: If set, makes a dbus async call, and the result will
        be sent to reply_handler. This must be a callable object.
    :param error_handler: If set, this callable will recieve any errors, and
        the call will be made asyncronously.
    :returns: A string containing introspection xml, if called synchronously.
    :raises ValueError: if one, but not both of 'reply_handler' and
        'error_handler' are set.

    """
    if callable(reply_handler) and callable(error_handler):
        backend.dbus_introspection_iface.Introspect(
            reply_handler=reply_handler,
            error_handler=error_handler,
        )
    elif reply_handler or error_handler:
        raise ValueError(
            "Both 'reply_handler' and 'error_handler' must be set."
        )
    else:
        return backend.dbus_introspection_iface.Introspect()


def _get_proxy_bases_from_introspection_xml(introspection_xml):
    """Return  tuple of the base classes to use when creating a proxy object.

    Currently this works by looking for certain interface names in the XML. In
    the future we may want to parse the XML and perform more rigerous checks.

    :param introspection_xml: An xml string that describes the exported object
        on the dbus backend. This determines which capabilities are present in
        the backend, and therefore which base classes should be used to create
        the proxy object.

    :raises: **RuntimeError** if the autopilot interface cannot be found.

    """
    bases = [ApplicationProxyObject]
    if AP_INTROSPECTION_IFACE not in introspection_xml:
        raise RuntimeError("Could not find Autopilot interface.")

    if QT_AUTOPILOT_IFACE in introspection_xml:
        from autopilot.introspection.qt import QtObjectProxyMixin
        bases.append(QtObjectProxyMixin)

    return tuple(bases)


def _extend_proxy_bases_with_emulator_base(proxy_bases, emulator_base):
    if emulator_base is None:
        emulator_base = type('DefaultEmulatorBase', (CustomEmulatorBase,), {})
    return proxy_bases + (emulator_base, )


def _get_proxy_object_class_name_and_state(
        backend, reply_handler=None, error_handler=None):
    """Get details about this autopilot backend via a dbus GetState call.

    :param reply_handler: A callable that must accept three positional
        arguments, which correspond to the return value of this function when
        called synchronously.

    :param error_handler: A callable which will recieve any dbus errors, should
        they occur.

    :raises ValueError: if one, but not both of reply_handler and error_handler
        are set.

    :returns: A tuple containing the class name of the root of the
        introspection tree, the full path to the root of the introspection
        tree, and the state dictionary of the root node in the introspection
        tree.

    """
    if callable(reply_handler) and callable(error_handler):
        # Async call:
        # Since we get an array of state, and we only care about the first one
        # we use a lambda to unpack it, and then so some trivial
        backend.introspection_iface.GetState(
            "/",
            reply_handler=lambda r: reply_handler(
                *_get_details_from_state_data(r[0])
            ),
            error_handler=error_handler,
        )
    elif reply_handler or error_handler:
        raise ValueError(
            "Both 'reply_handler' and 'error_handler' must be set."
        )
    else:
        # Sync call
        state = backend.introspection_iface.GetState("/")[0]
        return _get_details_from_state_data(state)


def _get_details_from_state_data(state_data):
    """Get details from a state data array.

    Returns class name, path, and state dictionary.
    """
    object_path, object_state = state_data
    return (
        get_classname_from_path(object_path),
        object_path,
        object_state,
    )


def _make_proxy_class_object(cls_name, proxy_bases):
    """Return a class object for a proxy.

    :param cls_name: The name of the class to be created. This is usually the
        type as returned over the wire from an autopilot backend.
    :param proxy_bases: A list of base classes this proxy class should derive
        from. This determines the specific abilities of the new proxy.

    """
    clsobj = type(str("%sBase" % cls_name), proxy_bases, {})
    proxy_class = type(str(cls_name), (clsobj,), {})
    return proxy_class


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
