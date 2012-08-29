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

import dbus
import gio
import logging
import subprocess
from testtools.content import text_content
from time import sleep

from autopilot.introspection.dbus import (
    AP_INTROSPECTION_IFACE,
    clear_object_registry,
    DBusIntrospectionObject,
    DBUS_INTROSPECTION_IFACE,
    object_passes_filters,
    session_bus,
    )

logger = logging.getLogger(__name__)

QT_AUTOPILOT_IFACE = 'com.canonical.Autopilot.Qt'
QT_AUTOPILOT_PATH = "/com/canonical/Autopilot/Introspection"

class ApplicationProxyObect(DBusIntrospectionObject):
    """A class that better supports query data from an application."""

    def __init__(self, state):
        super(ApplicationProxyObect, self).__init__(state)
        self._process = None

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


class QtSignalWatcher(object):

    """A utility class to make watching Qt signals easy."""

    def __init__(self, proxy, signal_name):
        """Initialise the signal watcher.

        'proxy' is an instance of QtObjectProxyMixin.
        'signal_name' is the name of the signal being monitored.

        Do not construct this object yourself. Instead, call 'watch_signal' on a
        QtObjectProxyMixin instance.

        """
        self._proxy = proxy
        self.signal_name = signal_name
        self._data = None

    def _refresh(self):
        self._data = self._proxy.get_signal_emissions(self.signal_name)

    @property
    def num_emissions(self):
        """Get the number of times the signal has been emitted since we started
        monitoring it.

        """
        self._refresh()
        return len(self._data)

    @property
    def was_emitted(self):
        """True if the signal was emitted at least once."""
        self._refresh()
        return len(self._data) > 0


class QtObjectProxyMixin(object):
    """A class containing methods specific to querying Qt applications."""

    def _get_qt_iface(self):
        """Get the autopilot Qt-specific interface for the specified service name
        and object path.

        """

        _debug_proxy_obj = session_bus.get_object(self.DBUS_SERVICE, self.DBUS_OBJECT)
        return dbus.Interface(_debug_proxy_obj, QT_AUTOPILOT_IFACE)

    def watch_signal(self, signal_name):
        """Start watching the 'signal_name' signal on this object.

        signal_name must be the C++ signal signature, as is usually used within
        the Qt 'SIGNAL' macro. Examples of valid signal names are:

         * 'clicked(bool)'
         * 'pressed()'

        A list of valid signal names can be retrieved from 'get_signals()'. If an
        invalid signal name is given ValueError will be raised.

        This method returns a QtSignalWatcher instance.

        By default, no signals are monitored. You must call this method once for
        each signal you are interested in.

        """
        valid_signals = self.get_signals()
        if signal_name not in valid_signals:
            raise ValueError("Signal name %r is not in the valid signal list of %r" % (signal_name, valid_signals))

        self._get_qt_iface().RegisterSignalInterest(self.id, signal_name)
        return QtSignalWatcher(self, signal_name)

    def get_signal_emissions(self, signal_name):
        """Get a list of all the emissions of the 'signal_name' signal.

        If signal_name is not a valid signal, ValueError is raised.

        The QtSignalWatcher class provides a more convenient API than calling
        this method directly. A QtSignalWatcher instance is returned from
        'watch_signal'.

        Each item in the returned list is a tuple containing the arguments in the
        emission (possibly an empty list if the signal has no arguments).

        If the signal was not emitted, the list will be empty. You must first
        call 'watch_signal(signal_name)' in order to monitor this signal.

        Note: Some signal arguments may not be marshallable over DBus. If this is
        the case, they will be omitted from the argument list.

        """
        valid_signals = self.get_signals()
        if signal_name not in valid_signals:
            raise ValueError("Signal name %r is not in the valid signal list of %r" % (signal_name, valid_signals))

        return self._get_qt_iface().GetSignalEmissions(self.id, signal_name)

    def get_signals(self):
        """Get a list of the signals available on this object."""
        dbus_signal_list = self._get_qt_iface().ListSignals(self.id)
        return [str(sig) for sig in dbus_signal_list]


class QtIntrospectionTestMixin(object):
    """A mix-in class to make Qt application introspection easier."""

    def launch_test_application(self, application, *arguments, **kwargs):
        """Launch 'application' and retrieve a proxy object for the application.

        Use this method to launch a supported application and start testing it.
        The application can be specified as:

         * A Desktop file, either with or without a path component.
         * An executable file, either with a path, or one that is in the $PATH.

        This method supports the following keyword arguments:

         * launch_dir. If set to a directory that exists the process will be
         launched from that directory.

        Unknown keyword arguments will cause a ValueError to be raised.

        This method returns a proxy object that represents the application.
        Introspection data is retrievable via this object.

         """
        if not isinstance(application, basestring):
            raise TypeError("'application' parameter must be a string.")
        cwd = kwargs.pop('launch_dir', None)
        if kwargs:
            raise ValueError("Unknown keyword arguments: %s." %
                (', '.join( repr(k) for k in kwargs.keys())))

        if application.endswith('.desktop'):
            proxy = launch_application_from_desktop_file(application, *arguments, cwd=cwd)
        else:
            proxy = launch_application_from_path(application, *arguments, cwd=cwd)

        self.addCleanup(self._kill_process_and_attach_logs, proxy)
        return proxy

    def _kill_process_and_attach_logs(self, proxy):
        process = proxy.process
        process.kill()
        stdout, stderr = process.communicate()
        self.addDetail('process-stdout', text_content(stdout))
        self.addDetail('process-stderr', text_content(stderr))


def launch_application_from_desktop_file(desktop_file, *arguments, **kwargs):
    """Launch an application from a desktop file.

    This function actually just finds the executable on disk and defers the
    real work to launch_application_from_path.

    """
    proc = gio.unix.DesktopAppInfo(desktop_file)
    return launch_application_from_path(proc.get_executable(), *arguments, **kwargs)


def launch_application_from_path(application_path, *arguments, **kwargs):
    arguments = list(arguments)
    if "-testability" not in arguments:
        arguments.insert(0, "-testability")

    return launch_autopilot_enabled_process(application_path, *arguments, **kwargs)


def launch_autopilot_enabled_process(application, *args, **kwargs):
    """Launch an autopilot-enabled process and return the proxy object."""
    commandline = [application]
    commandline.extend(args)
    process = subprocess.Popen(commandline,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        **kwargs)
    return get_autopilot_proxy_object_for_process(process)


def get_autopilot_proxy_object_for_process(process):
    """return the autopilot proxy object for the given process.

    Raises RuntimeError if no autopilot interface was found.

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

    bus_object = session_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    bus_iface = dbus.Interface(bus_object, 'org.freedesktop.DBus')

    # clear the object registry, since it's specific to the dbus service, and we
    # have just started a new service. We don't want the old types hanging around
    # in the registry. We need a better method for this however.
    clear_object_registry()

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
                    proxy = make_proxy_object_from_service_name(name, QT_AUTOPILOT_PATH)
                    proxy.set_process(process)
                    return proxy
            except Exception as e:
                print e
        sleep(1)
    raise RuntimeError("Unable to find Autopilot interface.")


def make_proxy_object_from_service_name(service_name, obj_path):
    """Returns a root proxy object given a DBus service name."""
    # parameters can sometimes be dbus.String instances, sometimes QString instances.
    # it's easier to convert them here than at the calling sites.
    service_name = str(service_name)
    obj_path = str(obj_path)
    dbus_object = session_bus.get_object(service_name, obj_path)
    introspection_iface = dbus.Interface(dbus_object, DBUS_INTROSPECTION_IFACE)
    intro_xml = introspection_iface.Introspect()
    if AP_INTROSPECTION_IFACE not in intro_xml:
        raise RuntimeError("Could not find Autopilot interface on service name '%s'" % service_name)

    dbus_iface = dbus.Interface(dbus_object, AP_INTROSPECTION_IFACE)
    cls_name, cls_state = dbus_iface.GetState("/")[0]

    # If this is a Qt-enabled application, add the QtObjectProxyMixin
    if QT_AUTOPILOT_IFACE in intro_xml:
        clsobj = type(str(cls_name),
            (ApplicationProxyObect, QtObjectProxyMixin),
            dict(DBUS_SERVICE=service_name,
                DBUS_OBJECT=obj_path
                )
            )
    else:
        clsobj = type(str(cls_name),
            (ApplicationProxyObect,),
            dict(DBUS_SERVICE=service_name,
                DBUS_OBJECT=obj_path
                )
            )
    proxy = clsobj(cls_state)
    return proxy
