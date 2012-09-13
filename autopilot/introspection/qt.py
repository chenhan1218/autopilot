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
import functools
import gio
import logging
import subprocess
from testtools.content import text_content

from autopilot.introspection import get_autopilot_proxy_object_for_process, QT_AUTOPILOT_IFACE
from autopilot.introspection.dbus import session_bus


logger = logging.getLogger(__name__)


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

    @property
    def slots(self):
        """An object that contains all the slots available to be called in this object."""
        if getattr(self, '_slots', None) is None:
            self._slots = QtSlotProxy(self)
        return self._slots

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

    def get_slots(self):
        """Get a list of the slots available on this object."""
        dbus_slot_list = self._get_qt_iface().ListMethods(self.id)
        return [str(sig) for sig in dbus_slot_list]


class QtSlotProxy(object):
    """A class that transparently calls slots in a Qt object."""

    def __init__(self, qt_mixin):
        self._dbus_iface = qt_mixin._get_qt_iface()
        self._object_id = qt_mixin.id

        methods = self._dbus_iface.ListMethods(self._object_id)
        for method_name in methods:
            method = functools.partial(self._call_method, method_name)
            stripped_method_name = method_name[:method_name.find('(')]
            setattr(self, stripped_method_name, method)

    def _call_method(self, name, *args):
        self._dbus_iface.InvokeMethod(self._object_id, name, args)


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
            proc = gio.unix.DesktopAppInfo(application)
            application = proc.get_executable()

        proxy = launch_application_from_path(application, *arguments, cwd=cwd)

        self.addCleanup(self._kill_process_and_attach_logs, proxy)
        return proxy

    def _kill_process_and_attach_logs(self, proxy):
        process = proxy.process
        process.kill()
        stdout, stderr = process.communicate()
        self.addDetail('process-stdout', text_content(stdout))
        self.addDetail('process-stderr', text_content(stderr))


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

