# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#

"""Package for introspection support.

This package contains the internal implementation of the autopilot introspection
mechanism, and probably isn't useful to most test authors.

"""

import dbus
import logging
import subprocess
from time import sleep
import os


from autopilot.introspection.constants import (
    AUTOPILOT_PATH,
    QT_AUTOPILOT_IFACE,
    AP_INTROSPECTION_IFACE,
    DBUS_INTROSPECTION_IFACE,
    )
from autopilot.introspection.dbus import (
    clear_object_registry,
    DBusIntrospectionObject,
    object_passes_filters,
    get_session_bus,
    get_classname_from_path,
    )
from autopilot.utilities import get_debug_logger, addCleanup


logger = logging.getLogger(__name__)


def get_application_launcher(app_path):
    """Return an instance of :class:`ApplicationLauncher` that knows how to launch
    the application at 'app_path'.
    """
    # TODO: this is a teeny bit hacky - we call ldd to check whether this application
    # links to certain library. We're assuming that linking to libQt* or libGtk*
    # means the application is introspectable. This excludes any non-dynamically
    # linked executables, which we may need to fix further down the line.
    try:
        ldd_output = subprocess.check_output(["ldd", app_path]).strip().lower()
    except subprocess.CalledProcessError as e:
        return None
    if 'libqtcore' in ldd_output or 'libqt5core' in ldd_output:
        from autopilot.introspection.qt import QtApplicationLauncher
        return QtApplicationLauncher()
    elif 'libgtk' in ldd_output:
        from autopilot.introspection.gtk import GtkApplicationLauncher
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
        raise ValueError("Unknown keyword arguments: %s." %
            (', '.join( repr(k) for k in kwargs.keys())))

    path, args = launcher.prepare_environment(application, list(arguments))

    process = launch_process(path,
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
        """Prepare the application, or environment to launch with autopilot-support.

        This method does nothing - it exists so child classes can override it.

        The method *must* return a tuple of (*app_path*, *arguments*). Either of
        these can be altered by this method.

        """
        raise NotImplementedError("Sub-classes must implement this method.")



def launch_process(application, args, capture_output, **kwargs):
    """Launch an autopilot-enabled process and return the proxy object."""
    commandline = [application]
    commandline.extend(args)
    logger.info("Launching process: %r", commandline)
    cap_mode = None
    if capture_output:
        cap_mode = subprocess.PIPE
    process = subprocess.Popen(commandline,
        stdin=subprocess.PIPE,
        stdout=cap_mode,
        stderr=cap_mode,
        close_fds=True,
        preexec_fn=os.setsid,
        **kwargs)
    return process


def get_autopilot_proxy_object_for_process(process):
    """Return the autopilot proxy object for the given *process*.

    :raises: **RuntimeError** if no autopilot interface was found.

    """
    pid = process.pid
    #
    # FIXME: Currently the libindicate python bindings provide no way of
    # getting a server property. Instead, the only thing we can do is to
    # iterate over every service in the session bus, grab the ones that
    # match the process id passed to us, and look for the autopilot interface
    # manually.
    #
    # This sucks, and should be changed to something more elegant in the future.
    session_bus = get_session_bus()
    bus_object = session_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    bus_iface = dbus.Interface(bus_object, 'org.freedesktop.DBus')

    # clear the object registry, since it's specific to the dbus service, and we
    # have just started a new service. We don't want the old types hanging around
    # in the registry. We need a better method for this however.
    clear_object_registry()

    logger.info("Looking for autopilot interface for PID %d (and children)", pid)
    # We give the process 10 seconds grace time to get the dbus interface up...
    for i in range(10):
        eligible_pids = get_child_pids(pid)
        get_debug_logger().debug("Searching for eligible PIDs: %r", eligible_pids)
        names = session_bus.list_names()
        for name in names:
            try:
                name_pid = bus_iface.GetConnectionUnixProcessID(name)
                if name_pid in eligible_pids:
                    # We've found at least one connection to the session bus from
                    # this PID. Might not be the one we want however...
                    proxy = make_proxy_object_from_service_name(name, AUTOPILOT_PATH)
                    proxy.set_process(process)
                    return proxy
            except Exception as e:
                logger.warning("Caught exception while searching for autopilot interface: '%r'", e)
        sleep(1)
    raise RuntimeError("Unable to find Autopilot interface.")


def get_child_pids(pid):
    """Get a list of all child process Ids, for the given parent.

    """
    def get_children(pid):
        command = ['ps', '-o', 'pid', '--ppid', str(pid), '--noheaders']
        try:
            raw_output = subprocess.check_output(command)
        except subprocess.CalledProcessError:
            return []
        return [int(p) for p in raw_output.split()]

    result = [pid]
    data = get_children(pid)
    while data:
        pid = data.pop(0)
        result.append(pid)
        data.extend(get_children(pid))

    return result


def make_proxy_object_from_service_name(service_name, obj_path):
    """Returns a root proxy object given a DBus service name."""
    # parameters can sometimes be dbus.String instances, sometimes QString instances.
    # it's easier to convert them here than at the calling sites.
    service_name = str(service_name)
    obj_path = str(obj_path)

    proxy_bases = get_proxy_object_base_clases(service_name, obj_path)
    cls_name, cls_state = get_proxy_object_class_name_and_state(service_name, obj_path)

    clsobj = type(str(cls_name),
        proxy_bases,
        dict(DBUS_SERVICE=service_name,
            DBUS_OBJECT=obj_path
            )
        )
    proxy = clsobj.get_root_instance()
    return proxy


def get_proxy_object_base_clases(service_name, obj_path):
    """Return  tuple of the base classes to use when creating a proxy object
    for the given service name & path.

    :raises: **RuntimeError** if the autopilot interface cannot be found.

    """

    bases = [ApplicationProxyObect]

    dbus_object = get_session_bus().get_object(service_name, obj_path)
    introspection_iface = dbus.Interface(dbus_object, DBUS_INTROSPECTION_IFACE)
    intro_xml = introspection_iface.Introspect()
    if AP_INTROSPECTION_IFACE not in intro_xml:
        raise RuntimeError("Could not find Autopilot interface on service name '%s'" % service_name)

    if QT_AUTOPILOT_IFACE in intro_xml:
        from autopilot.introspection.qt import QtObjectProxyMixin
        bases.append(QtObjectProxyMixin)

    return tuple(bases)


def get_proxy_object_class_name_and_state(service_name, obj_path):
    """Return the class name and root state dictionary."""
    dbus_object = get_session_bus().get_object(service_name, obj_path)
    dbus_iface = dbus.Interface(dbus_object, AP_INTROSPECTION_IFACE)
    object_path, object_state = dbus_iface.GetState("/")[0]
    return get_classname_from_path(object_path), object_state


class ApplicationProxyObect(DBusIntrospectionObject):
    """A class that better supports query data from an application."""

    def __init__(self, state, path_info=None):
        super(ApplicationProxyObect, self).__init__(state, path_info)
        self._process = None

    def select_single(self, type_name='*', **kwargs):
        """Get a single node from the introspection tree, with type equal to
        *type_name* and (optionally) matching the keyword filters present in
        *kwargs*.

        For example:

        >>> app.select_single('QPushButton', objectName='clickme')
        ... returns a QPushButton whose 'objectName' property is 'clickme'.

        If nothing is returned from the query, this method returns None.

        :raises: **ValueError** if the query returns more than one item. *If you
         want more than one item, use select_many instead*.

        """
        instances = self.select_many(type_name, **kwargs)
        if len(instances) > 1:
            raise ValueError("More than one item was returned for query")
        if not instances:
            return None
        return instances[0]

    def select_many(self, type_name='*', **kwargs):
        """Get a list of nodes from the introspection tree, with type equal to
        *type_name* and (optionally) matching the keyword filters present in
        *kwargs*.

        For example:

        >>> app.select_many('QPushButton', enabled=True)
        ... returns a list of QPushButtons that are enabled.

        If you only want to get one item, use select_single instead.

        """
        logger.debug("Selecting objects of %s with attributes: %r",
            'any type' if type_name == '*' else 'type ' + type_name,
            kwargs)

        path = "//%s" % type_name
        state_dicts = self.get_state_by_path(path)
        instances = [self.make_introspection_object(i) for i in state_dicts]
        return filter(lambda i: object_passes_filters(i, **kwargs), instances)

    def set_process(self, process):
        """Set the subprocess.Popen object of the process that this is a proxy for.

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
        """Kill the running process that this is a proxy for using 'kill `pid`'."""
        subprocess.call(["kill", "%d" % self._process.pid])
