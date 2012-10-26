# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#

"""Package for introspection support."""

import dbus
from gi.repository import Gio
import logging
import subprocess
from testtools.content import text_content
from time import sleep


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
    session_bus,
    )


logger = logging.getLogger(__name__)


class ApplicationIntrospectionTestMixin(object):
    """A mix-in class to make launching applications for introsection easier.

    .. important:: You should not instantiate this class directly. Instead, use
     one of the derived classes.

    """

    def launch_test_application(self, application, *arguments, **kwargs):
        """Launch *application* and retrieve a proxy object for the application.

        Use this method to launch a supported application and start testing it.
        The application can be specified as:

         * A Desktop file, either with or without a path component.
         * An executable file, either with a path, or one that is in the $PATH.

        This method supports the following keyword arguments:

         * launch_dir. If set to a directory that exists the process will be
           launched from that directory.

        :raises: **ValueError** if unknown keyword arguments are passed.
        :return: A proxy object that represents the application. Introspection
         data is retrievable via this object.

         """
        if not isinstance(application, basestring):
            raise TypeError("'application' parameter must be a string.")
        cwd = kwargs.pop('launch_dir', None)
        if kwargs:
            raise ValueError("Unknown keyword arguments: %s." %
                (', '.join( repr(k) for k in kwargs.keys())))

        if application.endswith('.desktop'):
            proc = Gio.DesktopAppInfo.new(application)
            application = proc.get_executable()

        path, args = self.prepare_environment(application, list(arguments))

        proxy = launch_autopilot_enabled_process(path, args, cwd=cwd)

        self.addCleanup(self._kill_process_and_attach_logs, proxy)
        return proxy

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with autopilot-support.

        This method does nothing - it exists so child classes can override it.

        The method *must* return a tuple of (app_path, arguments). Either of
        these can be altered by this method.

        """
        raise NotImplementedError("Sub-classes must implement this method.")

    def _kill_process_and_attach_logs(self, proxy):
        process = proxy.process
        process.kill()
        stdout, stderr = process.communicate()
        self.addDetail('process-stdout', text_content(stdout))
        self.addDetail('process-stderr', text_content(stderr))


def launch_autopilot_enabled_process(application, args, **kwargs):
    """Launch an autopilot-enabled process and return the proxy object."""
    commandline = [application]
    commandline.extend(args)
    logger.info("Launching process: %r", commandline)
    process = subprocess.Popen(commandline,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        **kwargs)
    return get_autopilot_proxy_object_for_process(process)


def get_autopilot_proxy_object_for_process(process):
    """Return the autopilot proxy object for the given process.

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

    bus_object = session_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    bus_iface = dbus.Interface(bus_object, 'org.freedesktop.DBus')

    # clear the object registry, since it's specific to the dbus service, and we
    # have just started a new service. We don't want the old types hanging around
    # in the registry. We need a better method for this however.
    clear_object_registry()

    logger.info("Looking for autopilot interface for PID %d", pid)
    # We give the process 10 seconds grace time to get the dbus interface up...
    for i in range(10):
        names = session_bus.list_names()
        for name in names:
            try:
                name_pid = bus_iface.GetConnectionUnixProcessID(name)
                if name_pid == pid:
                    # We've found at least one connection to the session bus from
                    # this PID. Might not be the one we want however...
                    proxy = make_proxy_object_from_service_name(name, AUTOPILOT_PATH)
                    proxy.set_process(process)
                    return proxy
            except Exception as e:
                logger.warning("Caught exception while searching for autopilot interface: '%r'", e)
        sleep(1)
    raise RuntimeError("Unable to find Autopilot interface.")


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
    proxy = clsobj(cls_state)
    return proxy


def get_proxy_object_base_clases(service_name, obj_path):
    """Return  tuple of the base classes to use when creating a proxy object
    for the given service name & path.

    This function will raise a RuntimeError if the autopilot interface cannot be
    found.

    """

    bases = [ApplicationProxyObect]

    dbus_object = session_bus.get_object(service_name, obj_path)
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
    dbus_object = session_bus.get_object(service_name, obj_path)
    dbus_iface = dbus.Interface(dbus_object, AP_INTROSPECTION_IFACE)
    return dbus_iface.GetState("/")[0]


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
