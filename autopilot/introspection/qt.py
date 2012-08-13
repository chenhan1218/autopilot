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
import indicate
# from Queue import Queue
import logging
import subprocess
from time import sleep

from autopilot.introspection.dbus import DBusIntrospectionObject

logger = logging.getLogger(__name__)

class QtIntrospectionTestMixin(object):
     """A mix-in class to make Qt/Gtk application introspection easier."""

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
            launch_application_from_desktop_file(application, *arguments)
        else:
            launch_application_from_path(application, *arguments)


def launch_application_from_desktop_file(desktop_file, *arguments):
    """Launch an application from a desktop file.

    This function actually just finds the executable on disk and defers the
    real work to launch_application_from_path.

    """
    proc = gio.unix.DesktopAppInfo(desktop_file)
    launch_application_from_path(proc.get_executable())


def launch_application_from_path(application_path, *arguments):
    arguments = list(arguments)
    if "-testability" not in arguments:
        arguments.insert(0, "-testability")

    return launch_autopilot_enabled_process(application_path, *arguments)


def launch_autopilot_enabled_process(application, *args):
    commandline = [application]
    commandline.extend(args)
    listener = IndicateListener(10)
    listener.start_listening()
    process = subprocess.Popen(commandline)
    dbus_address = listener.get_found_dbus_address(process.pid)
    print "DBus address to connect to is:", dbus_address

    if dbus_address is None:
        raise RuntimeError("Could not find autopilot DBus interface on target application")

    cls_name = "UnknownProxy"
    try:
        cls_name = open("/proc/%d/cmdline").read().split()[0] + "Proxy"
    except:
        pass
    clsobj = type(cls_name,
                (DBusIntrospectionObject,),
                dict(DBUS_SERVICE=dbus_address[0], DBUS_OBJECT=dbus_address[1]))
    return clsobj



class IndicateListener(object):

    def __init__(self, timeout):
        self.timeout = timeout
        self.listener = indicate.indicate_listener_ref_default()
        self.found_servers = []

    def start_listening(self):
        """Start listening for an autopilot indicator object."""
        self.listener.connect("server-added", self._on_server_found)
        # self.listener.connect("indicator-added", self._on_indicator_found)

    def _on_server_found(self, listener, server, server_type, *args):
        # print server, server_type
        if server_type == 'autopilot':
            self.found_servers.append(server)

    def _on_indicator_found(self, *args):
        print args

    def get_found_dbus_address(self, pid):
        """Return the found autopilot DBus address.

        Returns a tuple of: (bus_name, object_path, object_interface)

        ...or None if no autopilot interface was found that matches the PID.

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
        for i in range(self.timeout):
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
                        dbus_object = session_bus.get_object(name, "/")
                        dbus_iface = dbus.Interface(dbus_object, 'com.canonical.Autopilot.Introspection')
                        # THis next line will raise an exception if we have the wrong
                        # connection:
                        dbus_iface.GetState("/very/unlikely/to/match/anything")
                        target_iface_object = dbus_iface
                        break
                except:
                    pass
            if target_iface_object:
                return (target_iface_object.bus_name,
                    target_iface_object.object_path,
                    target_iface_object.dbus_interface)
            sleep(1)
        return None





