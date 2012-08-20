# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#

"""Classes and tools to support Qt introspection."""


__all__ = 'QtIntrospectionTetMixin'

import gio
import logging
import subprocess
from time import sleep

from autopilot.introspection.dbus import (
    DBusIntrospectionObject,
    object_passes_filters,
    )

logger = logging.getLogger(__name__)


class ApplicationProxyObect(DBusIntrospectionObject):
    """A class that better supports query data from an application."""

    def select_single(self, type_name='*', **kwargs):
        """Get a single node from the introspection tree, with type equal to 'type_name'
        and (optionally) matching the keyword filters present in kwargs. For example:

        >>> app.select_single('QPushButton', objectName='clickme')
        ... returns a QPushButton whose 'objectName' property is 'clickme'.

        If the query returns more than one item, a ValueError will be raised. If
        you want more than one item, use select_many instead.

        If nothing is returned from the query, this method returns None.

        """
        instances = self.select_many(type_name, **kwargs)
        if len(instances) > 1:
            raise ValueError("More than one item was returned for query")
        if not instances:
            return None
        return instances[0]

    def select_many(self, type_name='*', **kwargs):
        """Get a list of nodes from the introspection tree, with type equal to
        'type_name' and (optionally) matching the keyword filters present in
        kwargs. For example:

        >>> app.select_many('QPushButton', enabled=True)
        ... returns a list of QPushButtons that are enabled.

        If you only want to get one item, use select_single instead.

        """

        path = "//%s" % type_name
        state_dicts = self.get_state_by_path(path)
        instances = [self.make_introspection_object(i) for i in state_dicts]
        return filter(lambda i: object_passes_filters(i, **kwargs), instances)


class QtIntrospectionTestMixin(object):
     """A mix-in class to make Qt application introspection easier."""

     def launch_test_application(self, application, *arguments):
        """Launch 'application' and retrieve a proxy object for the application.

        Use this method to launch a supported application and start testing it.
        The application can be specified as:

         * A Desktop file, either with or without a path component.
         * An executable file, either with a path, or one that is in the $PATH.

         This method returns a proxy object that represents the application.
         Introspection data is retrievable via this object.

         """
        if not isinstance(application, basestring):
            raise TypeError("'application' parameter must be a string.")

        if application.endswith('.desktop'):
            proxy, pid = launch_application_from_desktop_file(application, *arguments)
        else:
            proxy, pid = launch_application_from_path(application, *arguments)

        self.addCleanup(lambda: subprocess.call(["kill", "%d" % pid]))
        return proxy


def launch_application_from_desktop_file(desktop_file, *arguments):
    """Launch an application from a desktop file.

    This function actually just finds the executable on disk and defers the
    real work to launch_application_from_path.

    """
    proc = gio.unix.DesktopAppInfo(desktop_file)
    return launch_application_from_path(proc.get_executable())


def launch_application_from_path(application_path, *arguments):
    arguments = list(arguments)
    if "-testability" not in arguments:
        arguments.insert(0, "-testability")

    return launch_autopilot_enabled_process(application_path, *arguments)


def launch_autopilot_enabled_process(application, *args):
    """Launch an autopilot-enabled process and return the proxy object."""
    commandline = [application]
    commandline.extend(args)
    process = subprocess.Popen(commandline,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return get_autopilot_proxy_object_for_process(process.pid), process.pid


def get_autopilot_proxy_object_for_process(pid):
    """return the autopilot proxy object for the given pid.

    Raises RuntimeError if no autopilot interface was found.

    """
    #
    # FIXME: Currently the libindicate python bindings provide no way of
    # getting a server property. Instead, the only thing we can do is to
    # iterate over every service in the session bus, grab the ones that
    # match the process id passed to us, and look for the autopilot interface
    # manually.
    #
    # This sucks, and should be changed to something more elegant in the future.
    from autopilot.emulators.dbus_handler import session_bus
    import dbus

    bus_object = session_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    bus_iface = dbus.Interface(bus_object, 'org.freedesktop.DBus')

    target_iface_object = None
    cls_name = "UnknownProxy"
    cls_state = {}

    logger.info("Looking for autopilot interface for PID %d", pid)

    for i in range(10):
        names = session_bus.list_names()
        for name in names:
            # We only care about anonymous names for now.
            if not name.startswith(":"):
                continue
            try:
                # Autopilot interface is always registered at "/" - for now.
                # dbus_object = session_bus.get_object(name, "/")
                # dbus_iface = dbus.Interface(dbus_object, )
                name_pid = bus_iface.GetConnectionUnixProcessID(name)
                if name_pid == pid:
                    # We've found at least one connection to the session bus from
                    # this PID. Might not be the one we want however...
                    dbus_object = session_bus.get_object(name, "/com/canonical/Autopilot/Introspection")
                    dbus_iface = dbus.Interface(dbus_object, 'com.canonical.Autopilot.Introspection')
                    # THis next line will raise an exception if we have the wrong
                    # connection:
                    cls_name, cls_state = dbus_iface.GetState("/")[0]
                    target_iface_object = dbus_iface
                    logger.debug("Found interface: %r", target_iface_object)
                    break
            except:
                pass
        if target_iface_object:
            break
        sleep(1)

    if not target_iface_object:
        raise RuntimeError("Could not find autopilot DBus interface on target application")

    # create the proxy object:
    clsobj = type(str(cls_name),
                (ApplicationProxyObect,),
                dict(
                    DBUS_SERVICE=target_iface_object.bus_name,
                    DBUS_OBJECT=target_iface_object.object_path
                    ))
    return clsobj(cls_state)
