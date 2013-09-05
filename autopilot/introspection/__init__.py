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
from time import sleep
from functools import partial
import os
import sys

from autopilot.introspection.backends import DBusAddress
from autopilot.introspection.constants import (
    AUTOPILOT_PATH,
    QT_AUTOPILOT_IFACE,
    AP_INTROSPECTION_IFACE,
)
from autopilot.introspection.dbus import (
    _clear_backends_for_proxy_object,
    CustomEmulatorBase,
    DBusIntrospectionObject,
    get_classname_from_path,
)
from autopilot.introspection.utilities import (
    _get_bus_connections_pid,
    _pid_is_running,
)
from autopilot.dbus_handler import (
    get_session_bus,
    get_system_bus,
    get_custom_bus,
)


logger = logging.getLogger(__name__)

# Keep track of known connections during search
connection_list = []

# py2 compatible alias for py3
if sys.version >= '3':
    basestring = str


class ProcessSearchError(RuntimeError):
    pass


def get_application_launcher(app_path):
    """Return an instance of :class:`ApplicationLauncher` that knows how to
    launch the application at 'app_path'.
    """
    # TODO: this is a teeny bit hacky - we call ldd to check whether this
    # application links to certain library. We're assuming that linking to
    # libQt* or libGtk* means the application is introspectable. This excludes
    # any non-dynamically linked executables, which we may need to fix further
    # down the line.
    try:
        ldd_output = subprocess.check_output(["ldd", app_path]).strip().lower()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e)
    if 'libqtcore' in ldd_output or 'libqt5core' in ldd_output:
        from autopilot.introspection.qt import QtApplicationLauncher
        return QtApplicationLauncher()
    elif 'libgtk' in ldd_output:
        from autopilot.introspection.gtk import GtkApplicationLauncher
        return GtkApplicationLauncher()
    return None


def get_application_launcher_from_string_hint(hint):
    """Return in instance of :class:`ApplicationLauncher` given a string
    hint."""
    from autopilot.introspection.qt import QtApplicationLauncher
    from autopilot.introspection.gtk import GtkApplicationLauncher

    hint = hint.lower()
    if hint == 'qt':
        return QtApplicationLauncher()
    elif hint == 'gtk':
        return GtkApplicationLauncher()
    return None


def launch_application(launcher, application, *arguments, **kwargs):
    """Launch an application, and return a process object.

    :param launcher: An instance of the :class:`ApplicationLauncher` class to
        prepare the environment before launching the application itself.
    """

    if not isinstance(application, basestring):
        raise TypeError("'application' parameter must be a string.")
    cwd = kwargs.pop('launch_dir', None)
    capture_output = kwargs.pop('capture_output', True)
    if kwargs:
        raise ValueError(
            "Unknown keyword arguments: %s." %
            (', '.join(repr(k) for k in kwargs.keys())))

    path, args = launcher.prepare_environment(application, list(arguments))

    process = launch_process(
        path,
        args,
        capture_output,
        cwd=cwd
    )
    return process


class ApplicationLauncher(object):
    """A class that knows how to launch an application with a certain type of
    introspection enabled.

    """

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        This method does nothing - it exists so child classes can override it.

        The method *must* return a tuple of (*app_path*, *arguments*). Either
        of these can be altered by this method.

        """
        raise NotImplementedError("Sub-classes must implement this method.")


def launch_process(application, args, capture_output, **kwargs):
    """Launch an autopilot-enabled process and return the process object."""
    commandline = [application]
    commandline.extend(args)
    logger.info("Launching process: %r", commandline)
    cap_mode = None
    if capture_output:
        cap_mode = subprocess.PIPE
    process = subprocess.Popen(
        commandline,
        stdin=subprocess.PIPE,
        stdout=cap_mode,
        stderr=cap_mode,
        close_fds=True,
        preexec_fn=os.setsid,
        **kwargs
    )
    return process


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

    :raises: RuntimeError if no search criteria match.
    :raises: RuntimeError if the search criteria results in many matches.

    """
    if process is not None:
        if pid is None:
            pid = process.pid
        elif pid != process.pid:
            raise RuntimeError("Supplied PID and process.pid do not match.")

    if pid is not None and not _pid_is_running(pid):
        raise ProcessSearchError("PID %d could not be found" % pid)

    dbus_addresses = _get_dbus_addresses_from_search_parameters(
        pid,
        dbus_bus,
        connection_name,
        object_path,
        process
    )

    if application_name:
        app_name_check_fn = lambda i: get_classname_from_path(
            i.introspection_iface.GetState('/')[0][0]) == application_name
        dbus_addresses = filter(app_name_check_fn, dbus_addresses)

    if dbus_addresses is None or len(dbus_addresses) == 0:
        raise ProcessSearchError("Search criteria returned no results")
    if len(dbus_addresses) > 1:
        raise RuntimeError("Search criteria returned multiple results")

    return _make_proxy_object(dbus_addresses[0], emulator_base)


def _get_dbus_addresses_from_search_parameters(
        pid, dbus_bus, connection_name, object_path, process):
    """Returns a list of :py:class: `DBusAddress` for all successfully matched
    criteria.

    """
    _reset_known_connection_list()

    for i in range(10):
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

        sleep(1)
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
    bus."""
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


def _get_child_pids(pid):
    """Get a list of all child process Ids, for the given parent.

    """
    def get_children(pid):
        command = ['ps', '-o', 'pid', '--ppid', str(pid), '--noheaders']
        try:
            raw_output = subprocess.check_output(command)
        except subprocess.CalledProcessError:
            return []
        return [int(p) for p in raw_output.split()]

    result = []
    data = get_children(pid)
    while data:
        pid = data.pop(0)
        result.append(pid)
        data.extend(get_children(pid))

    return result


def _make_proxy_object(data_source, emulator_base):
    """Returns a root proxy object given a DBus service name."""
    proxy_bases = _get_proxy_object_base_classes(data_source)
    if emulator_base is None:
        emulator_base = type('DefaultEmulatorBase', (CustomEmulatorBase,), {})
    proxy_bases = proxy_bases + (emulator_base, )
    cls_name, cls_state = _get_proxy_object_class_name_and_state(data_source)

    _clear_backends_for_proxy_object(emulator_base)
    clsobj = type(
        str(cls_name), proxy_bases, dict(_Backend=data_source)
    )

    proxy = clsobj.get_root_instance()
    return proxy


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


def _get_proxy_object_class_name_and_state(backend):
    """Return the class name and root state dictionary."""
    object_path, object_state = backend.introspection_iface.GetState("/")[0]
    return get_classname_from_path(object_path), object_state


class ApplicationProxyObject(DBusIntrospectionObject):
    """A class that better supports query data from an application."""

    def __init__(self, state, path):
        super(ApplicationProxyObject, self).__init__(state, path)
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
